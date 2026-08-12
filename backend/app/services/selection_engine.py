"""Evidence-based question selection for assessments (P0-010)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.services import question_intelligence as qi
from app.services.similarity import diversity_ok


def _eligible_pool(
    db: Session,
    *,
    course_id: int,
    subject_ids: Optional[List[int]] = None,
    topic_ids: Optional[List[int]] = None,
    difficulties: Optional[List[str]] = None,
    question_types: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
) -> List[models.Question]:
    statuses = statuses or ["ACTIVE"]
    q = db.query(models.Question).filter(
        models.Question.course_id == course_id,
        models.Question.status.in_(statuses),
    )
    if subject_ids:
        q = q.filter(models.Question.subject_id.in_(subject_ids))
    if topic_ids:
        q = q.filter(models.Question.topic_id.in_(topic_ids))
    if difficulties:
        q = q.filter(models.Question.difficulty.in_(difficulties))
    if question_types:
        q = q.filter(models.Question.question_type.in_(question_types))
    return q.all()


def rank_candidates(db: Session, questions: List[models.Question]) -> List[Dict[str, Any]]:
    ranked = []
    for q in questions:
        imp = qi.question_importance(db, q)
        ranked.append(
            {
                "question": q,
                "question_id": q.id,
                "importance_score": imp["importance_score"],
                "factors": imp["contributing_factors"],
                "subject_id": q.subject_id,
                "topic_id": q.topic_id,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "novelty_class": q.novelty_class or "NOVEL",
                "stem": q.stem,
            }
        )
    ranked.sort(key=lambda x: x["importance_score"], reverse=True)
    return ranked


def _select_with_constraints(
    ranked: List[Dict[str, Any]],
    *,
    total: int,
    subject_quotas: Optional[Dict[int, int]] = None,
    difficulty_quotas: Optional[Dict[str, int]] = None,
    reuse_mix: Optional[Dict[str, float]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Greedy constraint-aware selection with explainable ranking."""
    errors: List[str] = []
    selected: List[Dict[str, Any]] = []
    selected_texts: List[str] = []
    subj_count: Dict[int, int] = defaultdict(int)
    diff_count: Dict[str, int] = defaultdict(int)
    reuse_count: Dict[str, int] = defaultdict(int)

    reuse_mix = reuse_mix or {"NOVEL": 0.5, "CONCEPT_VARIANT": 0.4, "EXACT_PREVIOUS": 0.1}
    reuse_targets = {k: int(round(v * total)) for k, v in reuse_mix.items()}
    # fix rounding
    while sum(reuse_targets.values()) > total and reuse_targets:
        k = max(reuse_targets, key=reuse_targets.get)
        reuse_targets[k] -= 1
    while sum(reuse_targets.values()) < total:
        k = max(reuse_mix, key=reuse_mix.get)
        reuse_targets[k] = reuse_targets.get(k, 0) + 1

    def reuse_bucket(nc: str) -> str:
        if nc in ("EXACT_PREVIOUS", "SIMILAR"):
            return "EXACT_PREVIOUS"
        if nc == "CONCEPT_VARIANT":
            return "CONCEPT_VARIANT"
        return "NOVEL"

    for cand in ranked:
        if len(selected) >= total:
            break
        sid = cand["subject_id"]
        diff = cand["difficulty"]
        bucket = reuse_bucket(cand["novelty_class"])

        if subject_quotas and sid in subject_quotas:
            if subj_count[sid] >= subject_quotas[sid]:
                continue
        if difficulty_quotas and diff in difficulty_quotas:
            if diff_count[diff] >= difficulty_quotas[diff]:
                continue
        if reuse_targets.get(bucket, 0) <= reuse_count[bucket]:
            # soft: allow overflow into NOVEL if needed later
            if bucket != "NOVEL" or reuse_count["NOVEL"] >= reuse_targets.get("NOVEL", total):
                # still allow if no better options later — skip for now
                continue

        if not diversity_ok(selected_texts, cand["stem"]):
            continue

        selected.append(cand)
        selected_texts.append(cand["stem"])
        subj_count[sid] += 1
        diff_count[diff] += 1
        reuse_count[bucket] += 1

    # Fill remaining ignoring soft reuse caps but keep diversity + subject/diff hard caps
    if len(selected) < total:
        used = {c["question_id"] for c in selected}
        for cand in ranked:
            if len(selected) >= total:
                break
            if cand["question_id"] in used:
                continue
            sid = cand["subject_id"]
            diff = cand["difficulty"]
            if subject_quotas and sid in subject_quotas and subj_count[sid] >= subject_quotas[sid]:
                continue
            if difficulty_quotas and diff in difficulty_quotas and diff_count[diff] >= difficulty_quotas[diff]:
                continue
            if not diversity_ok(selected_texts, cand["stem"]):
                continue
            selected.append(cand)
            selected_texts.append(cand["stem"])
            subj_count[sid] += 1
            diff_count[diff] += 1
            used.add(cand["question_id"])

    if len(selected) < total:
        errors.append(f"Could only select {len(selected)} of {total} questions under constraints")

    return selected, errors


def select_questions(
    db: Session,
    *,
    course_id: int,
    total_questions: int,
    subject_distribution: Optional[Dict[int, int]] = None,
    topic_ids: Optional[List[int]] = None,
    difficulty_distribution: Optional[Dict[str, int]] = None,
    question_types: Optional[List[str]] = None,
    reuse_policy: str = "MIXED",
    reuse_mix: Optional[Dict[str, float]] = None,
    evidence_based: bool = True,
) -> Dict[str, Any]:
    """
    Ranked, constraint-satisfying selection.

    evidence_based=True applies topic priority / historical importance ranking
    (required for Grand/Final). Results are historically high-priority candidates —
    not predicted exact future exam questions.
    """
    # Ensure intelligence snapshots exist
    if evidence_based:
        qi.compute_and_store_topic_priorities(db, course_id)

    subject_ids = list(subject_distribution.keys()) if subject_distribution else None
    difficulties = list(difficulty_distribution.keys()) if difficulty_distribution else None
    pool = _eligible_pool(
        db,
        course_id=course_id,
        subject_ids=subject_ids,
        topic_ids=topic_ids,
        difficulties=difficulties,
        question_types=question_types,
        statuses=["ACTIVE"],
    )
    ranked = rank_candidates(db, pool) if evidence_based else [
        {
            "question": q,
            "question_id": q.id,
            "importance_score": 0.5,
            "factors": {},
            "subject_id": q.subject_id,
            "topic_id": q.topic_id,
            "difficulty": q.difficulty,
            "question_type": q.question_type,
            "novelty_class": q.novelty_class or "NOVEL",
            "stem": q.stem,
        }
        for q in pool
    ]

    if reuse_policy == "NOVEL":
        reuse_mix = {"NOVEL": 1.0, "CONCEPT_VARIANT": 0.0, "EXACT_PREVIOUS": 0.0}
    elif reuse_policy == "EXACT_PREVIOUS":
        reuse_mix = {"NOVEL": 0.0, "CONCEPT_VARIANT": 0.0, "EXACT_PREVIOUS": 1.0}
    elif reuse_policy == "CONCEPT_VARIANT":
        reuse_mix = {"NOVEL": 0.2, "CONCEPT_VARIANT": 0.8, "EXACT_PREVIOUS": 0.0}
    elif reuse_mix is None:
        reuse_mix = {"NOVEL": 0.5, "CONCEPT_VARIANT": 0.4, "EXACT_PREVIOUS": 0.1}

    selected, errors = _select_with_constraints(
        ranked,
        total=total_questions,
        subject_quotas=subject_distribution,
        difficulty_quotas=difficulty_distribution,
        reuse_mix=reuse_mix,
    )

    return {
        "selected": [
            {
                "question_id": s["question_id"],
                "importance_score": s["importance_score"],
                "subject_id": s["subject_id"],
                "topic_id": s["topic_id"],
                "difficulty": s["difficulty"],
                "question_type": s["question_type"],
                "novelty_class": s["novelty_class"],
                "ranking_factors": s["factors"],
                "evidence_label": "historically_high_priority",
            }
            for s in selected
        ],
        "questions": [s["question"] for s in selected],
        "errors": errors,
        "pool_size": len(pool),
        "disclaimer": (
            "Selected questions are historically high-priority / exam-relevant candidates "
            "based on available evidence. This is not a prediction of exact future examination questions."
        ),
    }


def select_for_blueprint_item(
    db: Session,
    assessment: models.Assessment,
    item: models.AssessmentBlueprintItem,
    used_ids: set[int],
    *,
    evidence_based: bool,
) -> Tuple[List[models.Question], List[str]]:
    """Select for a single blueprint row — used by Assessment Engine integration."""
    pool = (
        db.query(models.Question)
        .filter(
            models.Question.course_id == assessment.course_id,
            models.Question.subject_id == item.subject_id,
            models.Question.difficulty == item.difficulty,
            models.Question.status == "ACTIVE",
        )
    )
    if item.topic_id is not None:
        pool = pool.filter(models.Question.topic_id == item.topic_id)
    if item.subtopic_id is not None:
        pool = pool.filter(models.Question.subtopic_id == item.subtopic_id)
    candidates = [q for q in pool.all() if q.id not in used_ids]
    if len(candidates) < item.question_count:
        label = f"subject={item.subject_id} topic={item.topic_id} difficulty={item.difficulty}"
        return [], [
            f"Insufficient questions for {label}: need {item.question_count}, available {len(candidates)}"
        ]

    if evidence_based:
        ranked = rank_candidates(db, candidates)
        picks: List[models.Question] = []
        texts: List[str] = []
        for cand in ranked:
            if len(picks) >= item.question_count:
                break
            if not diversity_ok(texts, cand["stem"]):
                continue
            picks.append(cand["question"])
            texts.append(cand["stem"])
        if len(picks) < item.question_count:
            # fill without diversity soft-fail
            remaining = [c["question"] for c in ranked if c["question"].id not in {p.id for p in picks}]
            picks.extend(remaining[: item.question_count - len(picks)])
        return picks[: item.question_count], []

    import random

    return random.sample(candidates, item.question_count), []
