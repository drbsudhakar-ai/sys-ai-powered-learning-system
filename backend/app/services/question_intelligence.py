"""Historical analysis, topic priority, and question importance engines."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.constants import PRIORITY_LABELS


DEFAULT_WEIGHTS = {
    "w_historical_weightage": 0.25,
    "w_historical_frequency": 0.25,
    "w_concept_frequency": 0.15,
    "w_recent_trend": 0.15,
    "w_syllabus_importance": 0.10,
    "w_exam_pattern": 0.10,
}


def _get_weights(db: Session, course_id: int) -> Dict[str, float]:
    cfg = (
        db.query(models.PriorityWeightConfig)
        .filter(models.PriorityWeightConfig.course_id == course_id)
        .first()
    )
    if not cfg:
        cfg = db.query(models.PriorityWeightConfig).filter(
            models.PriorityWeightConfig.course_id.is_(None)
        ).first()
    if not cfg:
        return dict(DEFAULT_WEIGHTS)
    return {
        "w_historical_weightage": cfg.w_historical_weightage,
        "w_historical_frequency": cfg.w_historical_frequency,
        "w_concept_frequency": cfg.w_concept_frequency,
        "w_recent_trend": cfg.w_recent_trend,
        "w_syllabus_importance": cfg.w_syllabus_importance,
        "w_exam_pattern": cfg.w_exam_pattern,
    }


def _priority_label(score: float) -> str:
    if score >= 0.75:
        return "VERY_HIGH"
    if score >= 0.55:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def analyze_course_history(db: Session, course_id: int) -> Dict[str, Any]:
    papers = (
        db.query(models.HistoricalExamPaper)
        .filter(models.HistoricalExamPaper.course_id == course_id)
        .order_by(models.HistoricalExamPaper.exam_year.asc())
        .all()
    )
    total_papers = len(papers) or 1
    topic_paper_hits: Dict[int, set] = defaultdict(set)
    topic_marks: Dict[int, float] = defaultdict(float)
    topic_qcount: Dict[int, int] = defaultdict(int)
    concept_counts: Counter = Counter()
    subject_marks: Dict[int, float] = defaultdict(float)
    difficulty_counts: Counter = Counter()
    type_counts: Counter = Counter()
    year_topic: Dict[int, Counter] = defaultdict(Counter)
    total_marks_all = 0.0

    for paper in papers:
        for hq in paper.questions:
            if hq.topic_id:
                topic_paper_hits[hq.topic_id].add(paper.id)
                topic_qcount[hq.topic_id] += 1
                topic_marks[hq.topic_id] += float(hq.marks or 1)
                year_topic[paper.exam_year][hq.topic_id] += 1
            if hq.subject_id:
                subject_marks[hq.subject_id] += float(hq.marks or 1)
            total_marks_all += float(hq.marks or 1)
            if hq.difficulty:
                difficulty_counts[hq.difficulty] += 1
            if hq.question_type:
                type_counts[hq.question_type] += 1
            for tag in hq.concept_tags or []:
                concept_counts[str(tag)] += 1

    years = sorted(year_topic.keys())
    recent_years = set(years[-3:]) if years else set()
    older_years = set(years[:-3]) if len(years) > 3 else set()

    def trend_for_topic(tid: int) -> str:
        if not years:
            return "UNKNOWN"
        recent = sum(year_topic[y][tid] for y in recent_years)
        older = sum(year_topic[y][tid] for y in older_years) if older_years else recent
        if older == 0:
            return "INCREASING" if recent > 0 else "UNKNOWN"
        ratio = recent / max(older, 1)
        if ratio >= 1.25:
            return "INCREASING"
        if ratio <= 0.75:
            return "DECREASING"
        return "STABLE"

    topic_stats = {}
    for tid, paper_ids in topic_paper_hits.items():
        freq = len(paper_ids) / total_papers
        weight = (topic_marks[tid] / total_marks_all) if total_marks_all else 0.0
        topic_stats[tid] = {
            "historical_frequency": round(freq, 4),
            "avg_marks_weightage": round(weight * 100, 2),
            "recent_trend": trend_for_topic(tid),
            "question_appearances": topic_qcount[tid],
            "exams_appeared": len(paper_ids),
            "total_exams": len(papers),
        }

    subject_weight = {
        sid: round((m / total_marks_all) * 100, 2) if total_marks_all else 0.0
        for sid, m in subject_marks.items()
    }

    return {
        "course_id": course_id,
        "papers_analyzed": len(papers),
        "topic_stats": topic_stats,
        "subject_weightage_observed": subject_weight,
        "difficulty_distribution": dict(difficulty_counts),
        "question_type_distribution": dict(type_counts),
        "top_concepts": concept_counts.most_common(20),
        "disclaimer": (
            "Statistics reflect historical examination evidence only. "
            "They do not predict exact future examination questions."
        ),
    }


def compute_and_store_topic_priorities(db: Session, course_id: int) -> List[models.TopicIntelligenceSnapshot]:
    analysis = analyze_course_history(db, course_id)
    weights = _get_weights(db, course_id)
    topics = (
        db.query(models.Topic)
        .join(models.Subject, models.Subject.id == models.Topic.subject_id)
        .filter(models.Subject.course_id == course_id)
        .all()
    )
    tw_map = {
        tw.topic_id: tw
        for tw in db.query(models.TopicWeightage).all()
    }
    concept_total = sum(c for _, c in analysis["top_concepts"]) or 1
    concept_by_name = {k: v / concept_total for k, v in analysis["top_concepts"]}

    snapshots: List[models.TopicIntelligenceSnapshot] = []
    for topic in topics:
        stats = analysis["topic_stats"].get(topic.id, {})
        freq = float(stats.get("historical_frequency") or 0)
        weight_pct = float(stats.get("avg_marks_weightage") or 0) / 100.0
        trend = stats.get("recent_trend") or "UNKNOWN"
        trend_score = {"INCREASING": 1.0, "STABLE": 0.55, "DECREASING": 0.25, "UNKNOWN": 0.4}.get(trend, 0.4)
        tw = tw_map.get(topic.id)
        syllabus = float(tw.syllabus_importance) if tw and tw.syllabus_importance is not None else 0.5
        configured_weight = (float(tw.weight_percent) / 100.0) if tw else weight_pct
        # concept frequency for this topic: overlap tags on historical qs
        concept_score = 0.0
        hist_qs = (
            db.query(models.HistoricalExamQuestion)
            .filter(models.HistoricalExamQuestion.topic_id == topic.id)
            .all()
        )
        for hq in hist_qs:
            for tag in hq.concept_tags or []:
                concept_score += concept_by_name.get(str(tag), 0)
        concept_score = min(concept_score, 1.0)
        exam_pattern = configured_weight

        score = (
            weights["w_historical_weightage"] * weight_pct
            + weights["w_historical_frequency"] * freq
            + weights["w_concept_frequency"] * concept_score
            + weights["w_recent_trend"] * trend_score
            + weights["w_syllabus_importance"] * syllabus
            + weights["w_exam_pattern"] * exam_pattern
        )
        score = round(min(max(score, 0.0), 1.0), 4)
        label = _priority_label(score)
        factors = {
            "historical_weightage": round(weight_pct, 4),
            "historical_frequency": round(freq, 4),
            "concept_frequency": round(concept_score, 4),
            "recent_trend": trend,
            "recent_trend_score": trend_score,
            "syllabus_importance": syllabus,
            "exam_pattern_relevance": round(exam_pattern, 4),
            "weights_used": weights,
        }
        qcount = (
            db.query(models.Question)
            .filter(
                models.Question.topic_id == topic.id,
                models.Question.course_id == course_id,
                models.Question.status.in_(("ACTIVE", "APPROVED")),
            )
            .count()
        )
        concepts = []
        for hq in hist_qs:
            for tag in hq.concept_tags or []:
                concepts.append(str(tag))
        top_concepts = [c for c, _ in Counter(concepts).most_common(8)]

        snap = (
            db.query(models.TopicIntelligenceSnapshot)
            .filter(
                models.TopicIntelligenceSnapshot.topic_id == topic.id,
                models.TopicIntelligenceSnapshot.course_id == course_id,
            )
            .first()
        )
        if not snap:
            snap = models.TopicIntelligenceSnapshot(topic_id=topic.id, course_id=course_id)
            db.add(snap)
        snap.historical_frequency = freq
        snap.avg_marks_weightage = float(stats.get("avg_marks_weightage") or 0)
        snap.recent_trend = trend
        snap.priority_score = score
        snap.priority_label = label
        snap.contributing_factors = factors
        snap.question_count = qcount
        snap.frequently_tested_concepts = top_concepts
        snap.updated_at = datetime.now(timezone.utc)
        snapshots.append(snap)

    db.commit()
    for s in snapshots:
        db.refresh(s)
    return snapshots


def question_importance(db: Session, question: models.Question) -> Dict[str, Any]:
    snap = None
    if question.topic_id:
        snap = (
            db.query(models.TopicIntelligenceSnapshot)
            .filter(
                models.TopicIntelligenceSnapshot.topic_id == question.topic_id,
                models.TopicIntelligenceSnapshot.course_id == question.course_id,
            )
            .first()
        )
    topic_priority = float(snap.priority_score) if snap and snap.priority_score is not None else 0.4
    topic_label = snap.priority_label if snap else "MEDIUM"
    hist_freq = float(snap.historical_frequency) if snap and snap.historical_frequency is not None else 0.0
    trend = snap.recent_trend if snap else "UNKNOWN"
    trend_score = {"INCREASING": 1.0, "STABLE": 0.55, "DECREASING": 0.25, "UNKNOWN": 0.4}.get(trend, 0.4)
    quality = float(question.quality_score) if question.quality_score is not None else 0.7
    novelty = {"NOVEL": 0.85, "CONCEPT_VARIANT": 0.7, "SIMILAR": 0.45, "EXACT_PREVIOUS": 0.3}.get(
        question.novelty_class or "NOVEL", 0.7
    )
    # mild difficulty fit: prefer MEDIUM/HARD for grand readiness
    diff_fit = {"EASY": 0.55, "MEDIUM": 0.85, "HARD": 0.9, "ADVANCED": 0.75}.get(question.difficulty, 0.7)
    recency = 0.6
    if question.source_year:
        age = max(0, datetime.now().year - int(question.source_year))
        recency = max(0.3, 1.0 - age * 0.08)

    score = round(
        0.28 * topic_priority
        + 0.18 * hist_freq
        + 0.12 * trend_score
        + 0.18 * quality
        + 0.12 * diff_fit
        + 0.07 * novelty
        + 0.05 * recency,
        4,
    )
    return {
        "question_id": question.id,
        "importance_score": min(score, 1.0),
        "contributing_factors": {
            "topic_priority": topic_label,
            "topic_priority_score": topic_priority,
            "historical_frequency": hist_freq,
            "recent_trend": trend,
            "quality": quality,
            "difficulty_fit": diff_fit,
            "novelty": question.novelty_class or "NOVEL",
            "recency": round(recency, 4),
        },
        "disclaimer": (
            "Importance reflects historical exam relevance and configured academic factors. "
            "It does not claim exact prediction of future examination questions."
        ),
    }


def topic_intelligence_payload(db: Session, topic_id: int) -> Dict[str, Any]:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        return {}
    subject = db.query(models.Subject).filter(models.Subject.id == topic.subject_id).first()
    course_id = subject.course_id if subject else None
    snap = None
    if course_id:
        snap = (
            db.query(models.TopicIntelligenceSnapshot)
            .filter(
                models.TopicIntelligenceSnapshot.topic_id == topic_id,
                models.TopicIntelligenceSnapshot.course_id == course_id,
            )
            .first()
        )
        if not snap:
            compute_and_store_topic_priorities(db, course_id)
            snap = (
                db.query(models.TopicIntelligenceSnapshot)
                .filter(
                    models.TopicIntelligenceSnapshot.topic_id == topic_id,
                    models.TopicIntelligenceSnapshot.course_id == course_id,
                )
                .first()
            )

    questions = (
        db.query(models.Question)
        .filter(
            models.Question.topic_id == topic_id,
            models.Question.status.in_(("ACTIVE", "APPROVED")),
        )
        .order_by(models.Question.id.desc())
        .limit(20)
        .all()
    )
    ranked = sorted(
        ((q, question_importance(db, q)["importance_score"]) for q in questions),
        key=lambda x: x[1],
        reverse=True,
    )
    representative = [
        {
            "id": q.id,
            "stem": q.stem[:240],
            "difficulty": q.difficulty,
            "importance": score,
            "shortcut": q.shortcut,
            "common_traps": q.common_traps,
            "alternative_solution": q.alternative_solution,
        }
        for q, score in ranked[:5]
    ]
    patterns = []
    for q, _ in ranked[:8]:
        for tag in q.concept_tags or []:
            patterns.append(str(tag))
    pattern_counts = Counter(patterns).most_common(10)

    return {
        "topic": {"id": topic.id, "name": topic.name, "subject_id": topic.subject_id},
        "course_id": course_id,
        "priority": snap.priority_label if snap else "MEDIUM",
        "priority_score": snap.priority_score if snap else None,
        "exam_weightage": snap.avg_marks_weightage if snap else None,
        "historical_frequency": snap.historical_frequency if snap else None,
        "recent_trend": snap.recent_trend if snap else "UNKNOWN",
        "contributing_factors": snap.contributing_factors if snap else {},
        "frequently_tested_concepts": (snap.frequently_tested_concepts if snap else []) or [],
        "important_question_patterns": [{"pattern": p, "count": c} for p, c in pattern_counts],
        "representative_questions": representative,
        "shortcuts": [q.shortcut for q, _ in ranked if q.shortcut][:5],
        "alternative_solutions": [q.alternative_solution for q, _ in ranked if q.alternative_solution][:5],
        "common_traps": [q.common_traps for q, _ in ranked if q.common_traps][:5],
        "typical_difficulty": Counter(q.difficulty for q, _ in ranked).most_common(1)[0][0] if ranked else None,
        "estimated_solving_time_seconds": (
            int(sum(q.estimated_time_seconds or 90 for q, _ in ranked[:5]) / max(len(ranked[:5]), 1))
            if ranked
            else None
        ),
        "disclaimer": (
            "Topic intelligence is evidence-based on historical papers and bank metadata. "
            "It highlights historically high-priority and frequently tested concepts — "
            "not exact future examination questions."
        ),
    }
