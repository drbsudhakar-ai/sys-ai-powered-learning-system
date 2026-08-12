"""P0-012 Performance Analyzer — driven by real P0-011 PerformanceRecords."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.constants import ASSESSMENT_TYPES
from app.services import question_intelligence as qi


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _pct(obtained: float, available: float) -> Optional[float]:
    if available <= 0:
        return None
    return round(100.0 * obtained / available, 2)


def _accuracy(correct: int, attempted: int) -> Optional[float]:
    if attempted <= 0:
        return None
    return round(100.0 * correct / attempted, 2)


def _classify_gap(
    *,
    accuracy: Optional[float],
    n_questions: int,
    repeated_errors: int,
    importance: float,
    hard_weakness: bool,
) -> Tuple[str, float, Dict[str, Any]]:
    inference: Dict[str, Any] = {"kind": "SYSTEM_INFERENCE", "signals": []}
    if n_questions < 2 and repeated_errors < 2:
        return "ADEQUATE", 0.35, {
            **inference,
            "signals": ["insufficient_evidence_for_strong_classification"],
            "note": "Limited evidence; classification is provisional.",
        }

    score = 50.0 if accuracy is None else float(accuracy)
    if accuracy is not None:
        inference["signals"].append(f"accuracy={accuracy}")
    if repeated_errors >= 3:
        score -= 12 + min(importance, 1.0) * 10
        inference["signals"].append(f"repeated_errors={repeated_errors}")
    elif repeated_errors >= 2:
        score -= 6 + min(importance, 1.0) * 5
        inference["signals"].append(f"repeated_errors={repeated_errors}")
    if hard_weakness:
        score -= 8
        inference["signals"].append("hard_question_weakness")
    if importance >= 0.7 and (accuracy or 100) < 55:
        score -= 10
        inference["signals"].append("high_importance_weakness")

    if score >= 90:
        label = "MASTERED"
    elif score >= 80:
        label = "STRONG"
    elif score >= 65:
        label = "ADEQUATE"
    elif score >= 50:
        label = "DEVELOPING"
    elif score >= 35:
        label = "WEAK"
    else:
        label = "CRITICAL_GAP"

    confidence = min(0.95, 0.4 + 0.05 * min(n_questions, 10) + 0.05 * min(repeated_errors, 5))
    return label, round(confidence, 2), inference


def _trend_from_series(pcts: List[float]) -> str:
    if len(pcts) < 2:
        return "STABLE"
    first, last = pcts[0], pcts[-1]
    deltas = [pcts[i] - pcts[i - 1] for i in range(1, len(pcts))]
    sign_changes = sum(1 for i in range(1, len(deltas)) if deltas[i] * deltas[i - 1] < 0)
    avg_delta = sum(deltas) / len(deltas)
    mid = sum(pcts) / len(pcts)

    if sign_changes >= 2 and abs(avg_delta) < 5:
        return "FLUCTUATING"
    if last - first >= 8 and avg_delta > 0:
        if len(pcts) >= 3 and pcts[1] < pcts[0] and last > mid:
            return "RECOVERING"
        return "IMPROVING"
    if first - last >= 8 and avg_delta < 0:
        return "DECLINING"
    if abs(last - first) < 4 and abs(avg_delta) < 2:
        if max(pcts) - min(pcts) < 5 and len(pcts) >= 3:
            return "STAGNATING"
        return "STABLE"
    if last > first:
        return "IMPROVING"
    if last < first:
        return "DECLINING"
    return "STABLE"


def _importance_for_record(db: Session, rec: Optional[models.PerformanceRecord]) -> float:
    if not rec or not rec.question_id:
        return 0.4
    q = db.query(models.Question).filter(models.Question.id == rec.question_id).first()
    if not q:
        return 0.4
    try:
        return float(qi.question_importance(db, q).get("importance_score") or 0.4)
    except Exception:
        return 0.4


def _topic_priority(db: Session, course_id: int, topic_id: Optional[int]) -> float:
    if not topic_id:
        return 0.4
    snap = (
        db.query(models.TopicIntelligenceSnapshot)
        .filter(
            models.TopicIntelligenceSnapshot.course_id == course_id,
            models.TopicIntelligenceSnapshot.topic_id == topic_id,
        )
        .first()
    )
    if snap and snap.priority_score is not None:
        return float(snap.priority_score)
    return 0.4


def analyze_student_course(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    trigger_attempt_id: Optional[int] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    student = db.query(models.User).filter(models.User.id == student_id).first()
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not student or not course:
        return {}

    attempts = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.student_id == student_id,
            models.AssessmentAttempt.course_id == course_id,
            models.AssessmentAttempt.status == "EVALUATED",
        )
        .order_by(models.AssessmentAttempt.submitted_at.asc())
        .all()
    )
    records = (
        db.query(models.PerformanceRecord)
        .filter(
            models.PerformanceRecord.student_id == student_id,
            models.PerformanceRecord.course_id == course_id,
        )
        .all()
    )

    subjects = {s.id: s.name for s in db.query(models.Subject).filter(models.Subject.course_id == course_id).all()}
    topics = {t.id: t.name for t in db.query(models.Topic).all()}

    attempt_pcts: List[float] = []
    by_type: Dict[str, List[float]] = {t: [] for t in ASSESSMENT_TYPES}
    total_correct = total_incorrect = total_unanswered = 0
    time_vals: List[float] = []

    for at in attempts:
        pct = float(at.percentage) if at.percentage is not None else _pct(
            float(at.total_marks_obtained or 0), float(at.total_marks_available or 0)
        )
        if pct is not None:
            attempt_pcts.append(pct)
            a_type = (at.assessment.assessment_type if at.assessment else None) or "TOPIC_TEST"
            if a_type in by_type:
                by_type[a_type].append(pct)
        total_correct += int(at.correct_count or 0)
        total_incorrect += int(at.incorrect_count or 0)
        total_unanswered += int(at.unanswered_count or 0)
        if at.time_spent_seconds:
            time_vals.append(float(at.time_spent_seconds))

    overall_pct = round(sum(attempt_pcts) / len(attempt_pcts), 2) if attempt_pcts else None
    recent_pct = round(sum(attempt_pcts[-3:]) / len(attempt_pcts[-3:]), 2) if attempt_pcts else None
    course_trend = _trend_from_series(attempt_pcts)
    attempted_q = total_correct + total_incorrect
    overall = {
        "total_assessments": len(attempts),
        "completed_assessments": len(attempts),
        "average_percentage": overall_pct,
        "recent_percentage": recent_pct,
        "cumulative_percentage": overall_pct,
        "accuracy": _accuracy(total_correct, attempted_q),
        "correct": total_correct,
        "incorrect": total_incorrect,
        "unanswered": total_unanswered,
        "attempted": attempted_q,
        "average_time_seconds": round(sum(time_vals) / len(time_vals), 1) if time_vals else None,
        "trend": course_trend,
        "disclaimer": "Observed from evaluated attempts. Trends and readiness are analytical estimates.",
    }

    def _bucket():
        return {
            "questions": 0,
            "correct": 0,
            "incorrect": 0,
            "unanswered": 0,
            "marks_obtained": 0.0,
            "marks_available": 0.0,
            "time_sum": 0.0,
            "time_n": 0,
            "importance_sum": 0.0,
            "wrong_question_ids": [],
            "by_difficulty": defaultdict(lambda: {"correct": 0, "incorrect": 0, "n": 0}),
        }

    by_subject: Dict[Any, Dict] = defaultdict(_bucket)
    by_topic: Dict[Any, Dict] = defaultdict(_bucket)
    by_diff: Dict[str, Dict] = defaultdict(_bucket)
    by_concept: Dict[str, Dict] = defaultdict(_bucket)
    wrong_counts: Dict[int, int] = defaultdict(int)
    question_cache: Dict[int, models.Question] = {}

    for rec in records:
        imp = _importance_for_record(db, rec)
        targets = []
        if rec.subject_id is not None:
            targets.append((rec.subject_id, by_subject))
        if rec.topic_id is not None:
            targets.append((rec.topic_id, by_topic))
        targets.append((rec.difficulty or "UNKNOWN", by_diff))

        for key, bucket in targets:
            b = bucket[key]
            b["questions"] += 1
            b["marks_obtained"] += float(rec.marks_obtained or 0)
            b["marks_available"] += float(rec.marks_available or 0)
            b["importance_sum"] += imp
            if rec.response_time_seconds is not None:
                b["time_sum"] += float(rec.response_time_seconds)
                b["time_n"] += 1
            if rec.is_correct:
                b["correct"] += 1
            elif rec.is_unanswered:
                b["unanswered"] += 1
            else:
                b["incorrect"] += 1
                b["wrong_question_ids"].append(rec.question_id)
            if bucket in (by_subject, by_topic):
                d = rec.difficulty or "UNKNOWN"
                b["by_difficulty"][d]["n"] += 1
                if rec.is_correct:
                    b["by_difficulty"][d]["correct"] += 1
                elif rec.is_incorrect:
                    b["by_difficulty"][d]["incorrect"] += 1

        if rec.is_incorrect and rec.question_id:
            wrong_counts[rec.question_id] += 1

        if rec.question_id:
            if rec.question_id not in question_cache:
                question_cache[rec.question_id] = (
                    db.query(models.Question).filter(models.Question.id == rec.question_id).first()
                )
            q = question_cache[rec.question_id]
            for tag in (q.concept_tags if q and q.concept_tags else []) or []:
                if not tag:
                    continue
                c = by_concept[str(tag)]
                c["questions"] += 1
                c["marks_obtained"] += float(rec.marks_obtained or 0)
                c["marks_available"] += float(rec.marks_available or 0)
                c["importance_sum"] += imp
                if rec.is_correct:
                    c["correct"] += 1
                elif rec.is_unanswered:
                    c["unanswered"] += 1
                else:
                    c["incorrect"] += 1

    def _finalize_scope(raw: Dict, name_fn, scope_type: str) -> List[Dict[str, Any]]:
        out = []
        for key, b in raw.items():
            avail = b["marks_available"]
            attempted = b["correct"] + b["incorrect"]
            acc = _accuracy(b["correct"], attempted)
            avg_imp = (b["importance_sum"] / b["questions"]) if b["questions"] else 0.4
            if scope_type == "TOPIC" and isinstance(key, int):
                avg_imp = max(avg_imp, _topic_priority(db, course_id, key))
            repeated = sum(1 for qid in set(b["wrong_question_ids"]) if wrong_counts.get(qid, 0) >= 2)
            hard = b["by_difficulty"].get("HARD") or b["by_difficulty"].get("ADVANCED") or {}
            hard_weak = bool(hard.get("n") and hard.get("incorrect", 0) >= max(1, hard.get("n", 1) // 2))
            classification, confidence, inference = _classify_gap(
                accuracy=acc,
                n_questions=b["questions"],
                repeated_errors=repeated
                + sum(max(0, wrong_counts.get(qid, 0) - 1) for qid in set(b["wrong_question_ids"])),
                importance=avg_imp,
                hard_weakness=hard_weak,
            )
            evidence = {
                "kind": "OBSERVED_EVIDENCE",
                "questions": b["questions"],
                "correct": b["correct"],
                "incorrect": b["incorrect"],
                "unanswered": b["unanswered"],
                "accuracy": acc,
                "percentage": _pct(b["marks_obtained"], avail),
                "avg_importance": round(avg_imp, 3),
                "repeated_error_questions": repeated,
                "avg_time_seconds": round(b["time_sum"] / b["time_n"], 1) if b["time_n"] else None,
                "difficulty_breakdown": {
                    d: {"n": v["n"], "correct": v["correct"], "incorrect": v["incorrect"]}
                    for d, v in b["by_difficulty"].items()
                },
            }
            out.append(
                {
                    "id": key if isinstance(key, int) else None,
                    "name": name_fn(key),
                    "scope_type": scope_type,
                    "classification": classification,
                    "confidence": confidence,
                    "priority_score": round(avg_imp, 3),
                    "is_high_priority": classification in ("WEAK", "CRITICAL_GAP") and avg_imp >= 0.55,
                    "percentage": evidence["percentage"],
                    "accuracy": acc,
                    "observed_evidence": evidence,
                    "system_inference": inference,
                }
            )
        out.sort(key=lambda x: (0 if x["is_high_priority"] else 1, x.get("percentage") or 0))
        return out

    subject_perf = _finalize_scope(by_subject, lambda i: subjects.get(i, str(i)), "SUBJECT")
    topic_perf = _finalize_scope(by_topic, lambda i: topics.get(i, str(i)), "TOPIC")
    difficulty_perf = _finalize_scope(by_diff, lambda i: i, "DIFFICULTY")
    concept_perf = _finalize_scope(by_concept, lambda i: i, "CONCEPT")

    assessment_type_performance = []
    for a_type in ASSESSMENT_TYPES:
        series = by_type.get(a_type) or []
        assessment_type_performance.append(
            {
                "assessment_type": a_type,
                "count": len(series),
                "average_percentage": round(sum(series) / len(series), 2) if series else None,
                "trend": _trend_from_series(series) if series else None,
                "latest_percentage": series[-1] if series else None,
            }
        )

    trends = {
        "course": course_trend,
        "by_assessment_type": {r["assessment_type"]: r["trend"] for r in assessment_type_performance if r["trend"]},
        "by_subject": {},
        "disclaimer": "Trend labels are SYSTEM_INFERENCE from chronological evaluated attempts.",
    }
    subject_series: Dict[int, List[float]] = defaultdict(list)
    for at in attempts:
        rows = [r for r in records if r.attempt_id == at.id and r.subject_id]
        by_s: Dict[int, Dict[str, float]] = defaultdict(lambda: {"o": 0.0, "a": 0.0})
        for r in rows:
            by_s[r.subject_id]["o"] += float(r.marks_obtained or 0)
            by_s[r.subject_id]["a"] += float(r.marks_available or 0)
        for sid, v in by_s.items():
            p = _pct(v["o"], v["a"])
            if p is not None:
                subject_series[sid].append(p)
    for sid, series in subject_series.items():
        trends["by_subject"][subjects.get(sid, str(sid))] = _trend_from_series(series)

    repeated_errors = []
    for qid, cnt in sorted(wrong_counts.items(), key=lambda x: -x[1]):
        if cnt < 2:
            continue
        sample = next((r for r in records if r.question_id == qid), None)
        repeated_errors.append(
            {"question_id": qid, "incorrect_count": cnt, "importance": _importance_for_record(db, sample)}
        )
        if len(repeated_errors) >= 20:
            break

    gaps = [g for g in (subject_perf + topic_perf + concept_perf) if g["classification"] in ("DEVELOPING", "WEAK", "CRITICAL_GAP")]
    strengths = [g for g in (subject_perf + topic_perf) if g["classification"] in ("MASTERED", "STRONG")]
    high_priority_gaps = [g for g in gaps if g.get("is_high_priority")]

    type_weights = {
        "TOPIC_TEST": 0.15,
        "WEEKLY_TEST": 0.15,
        "MONTHLY_TEST": 0.20,
        "GRAND_TEST": 0.25,
        "FINAL_GRAND_TEST": 0.25,
    }
    weighted = wsum = 0.0
    for row in assessment_type_performance:
        if row["average_percentage"] is None:
            continue
        w = type_weights.get(row["assessment_type"], 0.1)
        weighted += row["average_percentage"] * w
        wsum += w
    readiness_overall = round(weighted / wsum, 2) if wsum else overall_pct
    readiness = {
        "overall_estimate": readiness_overall,
        "subject_readiness": [
            {"id": s["id"], "name": s["name"], "estimate": s["percentage"], "classification": s["classification"]}
            for s in subject_perf
        ],
        "topic_readiness": [
            {"id": t["id"], "name": t["name"], "estimate": t["percentage"], "classification": t["classification"]}
            for t in topic_perf[:30]
        ],
        "difficulty_readiness": [{"name": d["name"], "estimate": d["percentage"]} for d in difficulty_perf],
        "cumulative_test_readiness": next(
            (r["average_percentage"] for r in assessment_type_performance if r["assessment_type"] == "GRAND_TEST"),
            None,
        ),
        "final_exam_readiness": next(
            (r["average_percentage"] for r in assessment_type_performance if r["assessment_type"] == "FINAL_GRAND_TEST"),
            readiness_overall,
        ),
        "label": "ANALYTICAL_ESTIMATE",
        "disclaimer": "Exam readiness is an analytical estimate, not a guarantee of examination outcome.",
    }

    recommended_focus = [
        {"name": g["name"], "classification": g["classification"], "scope_type": g["scope_type"], "reason": "high_priority_gap"}
        for g in high_priority_gaps[:5]
    ] or [
        {"name": g["name"], "classification": g["classification"], "scope_type": g["scope_type"], "reason": "developing_area"}
        for g in gaps[:5]
    ]

    profile = {
        "student_id": student_id,
        "course_id": course_id,
        "overall_performance": overall,
        "strengths": [{"name": s["name"], "classification": s["classification"], "percentage": s["percentage"]} for s in strengths[:10]],
        "developing_areas": [
            {"name": g["name"], "classification": g["classification"], "percentage": g["percentage"]}
            for g in gaps
            if g["classification"] == "DEVELOPING"
        ][:10],
        "learning_gaps": gaps,
        "high_priority_gaps": high_priority_gaps,
        "topic_performance": topic_perf,
        "subject_performance": subject_perf,
        "concept_performance": concept_perf,
        "difficulty_performance": difficulty_perf,
        "assessment_type_performance": assessment_type_performance,
        "trends": trends,
        "readiness": readiness,
        "repeated_errors": repeated_errors,
        "recommended_focus": recommended_focus,
        "evidence": {
            "attempt_count": len(attempts),
            "performance_record_count": len(records),
            "source": "P0-011_EVALUATED_ATTEMPTS",
        },
        "ai_lecturer_contract": {
            "student_id": student_id,
            "course_id": course_id,
            "high_priority_gaps": high_priority_gaps,
            "topic_performance": topic_perf,
            "strengths": strengths[:10],
            "readiness": readiness,
            "p010_topic_intelligence_refs": True,
        },
        "generated_at": _utcnow().isoformat(),
    }

    analysis = {
        "student": {"id": student.id, "name": student.name, "roll_number": student.roll_number},
        "course": {"id": course.id, "title": course.title},
        "overall": overall,
        "subject_performance": subject_perf,
        "topic_performance": topic_perf,
        "concept_performance": concept_perf,
        "difficulty_performance": difficulty_perf,
        "assessment_type_performance": assessment_type_performance,
        "trends": trends,
        "learning_gaps": gaps,
        "high_priority_gaps": high_priority_gaps,
        "strengths": strengths,
        "readiness": readiness,
        "repeated_errors": repeated_errors,
        "recommended_focus": recommended_focus,
        "profile": profile,
        "trigger_attempt_id": trigger_attempt_id,
        "generated_at": profile["generated_at"],
    }

    if persist:
        _persist_analysis(db, student_id, course_id, analysis, profile, trigger_attempt_id)
    return analysis


def _persist_analysis(
    db: Session,
    student_id: int,
    course_id: int,
    analysis: Dict[str, Any],
    profile: Dict[str, Any],
    trigger_attempt_id: Optional[int],
) -> None:
    row = (
        db.query(models.PerformanceAnalysis)
        .filter(
            models.PerformanceAnalysis.student_id == student_id,
            models.PerformanceAnalysis.course_id == course_id,
        )
        .first()
    )
    if not row:
        row = models.PerformanceAnalysis(student_id=student_id, course_id=course_id)
        db.add(row)
    row.analysis_json = analysis
    row.overall_percentage = (analysis.get("overall") or {}).get("average_percentage")
    row.trend = (analysis.get("overall") or {}).get("trend")
    row.readiness_estimate = (analysis.get("readiness") or {}).get("overall_estimate")
    row.trigger_attempt_id = trigger_attempt_id
    row.generated_at = _utcnow()
    db.flush()

    db.query(models.LearningGap).filter(
        models.LearningGap.student_id == student_id,
        models.LearningGap.course_id == course_id,
    ).delete()
    for g in analysis.get("learning_gaps") or []:
        db.add(
            models.LearningGap(
                student_id=student_id,
                course_id=course_id,
                analysis_id=row.id,
                scope_type=g.get("scope_type") or "TOPIC",
                scope_id=g.get("id") if isinstance(g.get("id"), int) else None,
                scope_name=g.get("name"),
                classification=g.get("classification") or "DEVELOPING",
                confidence=g.get("confidence"),
                priority_score=g.get("priority_score"),
                evidence=g.get("observed_evidence"),
                inference=g.get("system_inference"),
                is_high_priority=bool(g.get("is_high_priority")),
            )
        )

    pref = (
        db.query(models.StudentLearningProfile)
        .filter(
            models.StudentLearningProfile.student_id == student_id,
            models.StudentLearningProfile.course_id == course_id,
        )
        .first()
    )
    if not pref:
        pref = models.StudentLearningProfile(student_id=student_id, course_id=course_id)
        db.add(pref)
    pref.profile_json = profile
    pref.analysis_id = row.id
    pref.generated_at = _utcnow()
    db.commit()


def run_post_evaluation_pipeline(db: Session, attempt: models.AssessmentAttempt) -> Dict[str, Any]:
    from app.services import notifications as notif_svc

    analysis = analyze_student_course(
        db,
        student_id=attempt.student_id,
        course_id=attempt.course_id,
        trigger_attempt_id=attempt.id,
        persist=True,
    )
    if not analysis:
        return {}

    a_type = attempt.assessment.assessment_type if attempt.assessment else None
    link = f"/performance/student?student_id={attempt.student_id}&course_id={attempt.course_id}"
    overall = analysis.get("overall") or {}
    readiness = analysis.get("readiness") or {}

    try:
        notif_svc.emit_event(
            db,
            event="RESULT_AVAILABLE",
            title="Assessment result available",
            message=(
                f"Result available for assessment {attempt.assessment_id}. "
                f"Score {attempt.total_marks_obtained}/{attempt.total_marks_available} ({attempt.percentage}%)."
            ),
            student_id=attempt.student_id,
            course_id=attempt.course_id,
            assessment_id=attempt.assessment_id,
            severity="INFO",
            link_path=f"/student/attempts/{attempt.id}/result",
            payload={"attempt_id": attempt.id, "percentage": attempt.percentage},
            source_module="ASSESSMENT",
        )
        notif_svc.emit_event(
            db,
            event="PERFORMANCE_ANALYSIS_AVAILABLE",
            title="Performance analysis available",
            message=(
                f"Updated performance analysis. Overall {overall.get('average_percentage')}%. "
                f"Trend: {overall.get('trend')}. Readiness estimate: {readiness.get('overall_estimate')}%."
            ),
            student_id=attempt.student_id,
            course_id=attempt.course_id,
            assessment_id=attempt.assessment_id,
            severity="INFO",
            link_path=link,
            payload={
                "overall": overall.get("average_percentage"),
                "trend": overall.get("trend"),
                "readiness": readiness.get("overall_estimate"),
                "priority_areas": [x.get("name") for x in (analysis.get("recommended_focus") or [])[:3]],
            },
            source_module="PERFORMANCE_ANALYZER",
        )
        if a_type == "GRAND_TEST":
            notif_svc.emit_event(
                db,
                event="GRAND_ASSESSMENT_ANALYSIS",
                title="Grand assessment analysis",
                message=f"Grand test analysis updated (attempt {attempt.id}).",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                assessment_id=attempt.assessment_id,
                link_path=link,
                source_module="PERFORMANCE_ANALYZER",
            )
        if a_type == "FINAL_GRAND_TEST":
            notif_svc.emit_event(
                db,
                event="FINAL_GRAND_ASSESSMENT_ANALYSIS",
                title="Final Grand assessment analysis",
                message=f"Final Grand analysis updated (attempt {attempt.id}).",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                assessment_id=attempt.assessment_id,
                severity="WARNING",
                link_path=link,
                source_module="PERFORMANCE_ANALYZER",
            )
        if overall.get("trend") == "DECLINING":
            notif_svc.emit_event(
                db,
                event="SIGNIFICANT_PERFORMANCE_DECLINE",
                title="Performance decline detected",
                message="Analytical signal: performance trend appears declining.",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                severity="WARNING",
                link_path=link,
                source_module="PERFORMANCE_ANALYZER",
            )
        if overall.get("trend") == "IMPROVING":
            notif_svc.emit_event(
                db,
                event="SIGNIFICANT_IMPROVEMENT",
                title="Performance improvement detected",
                message="Analytical signal: performance trend appears improving.",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                severity="SUCCESS",
                link_path=link,
                source_module="PERFORMANCE_ANALYZER",
            )
        for g in (analysis.get("high_priority_gaps") or [])[:3]:
            evt = "CRITICAL_LEARNING_GAP" if g.get("classification") == "CRITICAL_GAP" else "REPEATED_WEAKNESS"
            notif_svc.emit_event(
                db,
                event=evt,
                title=f"{'Critical learning gap' if evt == 'CRITICAL_LEARNING_GAP' else 'Repeated weakness'}: {g.get('name')}",
                message=f"Evidence-based analytical signal for {g.get('name')} (confidence {g.get('confidence')}).",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                severity="CRITICAL" if evt == "CRITICAL_LEARNING_GAP" else "WARNING",
                link_path=link,
                payload={"gap": g},
                source_module="PERFORMANCE_ANALYZER",
            )
        notif_svc.emit_event(
            db,
            event="EXAM_READINESS_UPDATED",
            title="Exam readiness estimate updated",
            message=f"Readiness estimate: {readiness.get('overall_estimate')}%. {readiness.get('disclaimer')}",
            student_id=attempt.student_id,
            course_id=attempt.course_id,
            link_path=link,
            source_module="PERFORMANCE_ANALYZER",
        )
    except Exception:
        pass
    return analysis
