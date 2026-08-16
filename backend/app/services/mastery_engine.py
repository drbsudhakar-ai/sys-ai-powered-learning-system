"""P0-015 Adaptive Practice & Mastery Engine.

Deterministic, policy-driven mastery decisions. Reuses P0-010 selection,
P0-011 assessments/attempts, P0-012 analyzer/profile, P0-013 sessions (optional),
and P0-014 interventions (optional — never required for reassessment).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, roles
from app.academic_auth import can_manage_learning_sessions, is_admin
from app.constants import (
    DEFAULT_MASTERY_THRESHOLD,
    DEFAULT_MIN_REASSESSMENT_QUESTIONS,
    DEFAULT_PRACTICE_THRESHOLD,
    DEFAULT_REASSESSMENT_THRESHOLD,
    DEFAULT_REGRESSION_DROP_POINTS,
    DIFFICULTIES,
    REMEDIATION_SOURCES,
)
from app.services import assessment_engine as aeng
from app.services import notifications as notif_svc
from app.services import selection_engine as sel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _authorize_view(db: Session, actor: models.User, student_id: int, course_id: int) -> None:
    if not notif_svc.user_can_view_student_performance(db, actor, student_id, course_id):
        raise _http(403, "Not authorized for this student/course mastery")


def _authorize_self_or_staff(db: Session, actor: models.User, student_id: int, course_id: int) -> None:
    role = (actor.role or "").lower()
    if role == "student":
        if actor.id != student_id:
            raise _http(403, "Students may only manage their own mastery practice")
        enr = (
            db.query(models.StudentCourseEnrollment)
            .filter(
                models.StudentCourseEnrollment.student_id == actor.id,
                models.StudentCourseEnrollment.course_id == course_id,
            )
            .first()
        )
        if not enr:
            raise _http(403, "Not enrolled in this course")
        return
    _authorize_view(db, actor, student_id, course_id)


def get_policy(db: Session, course_id: Optional[int] = None) -> Dict[str, Any]:
    row = None
    if course_id is not None:
        row = (
            db.query(models.MasteryPolicy)
            .filter(models.MasteryPolicy.course_id == course_id)
            .first()
        )
    if not row:
        row = (
            db.query(models.MasteryPolicy)
            .filter(models.MasteryPolicy.course_id.is_(None))
            .first()
        )
    if row:
        return {
            "course_id": row.course_id,
            "mastery_threshold": float(row.mastery_threshold),
            "practice_threshold": float(row.practice_threshold),
            "reassessment_threshold": float(row.reassessment_threshold),
            "min_reassessment_questions": int(row.min_reassessment_questions),
            "regression_drop_points": float(row.regression_drop_points),
            "source": "course" if row.course_id else "global",
        }
    return {
        "course_id": course_id,
        "mastery_threshold": DEFAULT_MASTERY_THRESHOLD,
        "practice_threshold": DEFAULT_PRACTICE_THRESHOLD,
        "reassessment_threshold": DEFAULT_REASSESSMENT_THRESHOLD,
        "min_reassessment_questions": DEFAULT_MIN_REASSESSMENT_QUESTIONS,
        "regression_drop_points": DEFAULT_REGRESSION_DROP_POINTS,
        "source": "default",
    }


def upsert_policy(
    db: Session,
    actor: models.User,
    *,
    course_id: Optional[int],
    mastery_threshold: Optional[float] = None,
    practice_threshold: Optional[float] = None,
    reassessment_threshold: Optional[float] = None,
    min_reassessment_questions: Optional[int] = None,
    regression_drop_points: Optional[float] = None,
) -> Dict[str, Any]:
    if course_id is None:
        if not is_admin(actor):
            raise _http(403, "Only admin may set global mastery policy")
    else:
        if not can_manage_learning_sessions(db, actor, course_id=course_id):
            raise _http(403, "Not authorized to configure mastery policy for this course")
    q = db.query(models.MasteryPolicy)
    row = (
        q.filter(models.MasteryPolicy.course_id == course_id).first()
        if course_id is not None
        else q.filter(models.MasteryPolicy.course_id.is_(None)).first()
    )
    if not row:
        row = models.MasteryPolicy(course_id=course_id)
        db.add(row)
    if mastery_threshold is not None:
        row.mastery_threshold = float(mastery_threshold)
    if practice_threshold is not None:
        row.practice_threshold = float(practice_threshold)
    if reassessment_threshold is not None:
        row.reassessment_threshold = float(reassessment_threshold)
    if min_reassessment_questions is not None:
        row.min_reassessment_questions = int(min_reassessment_questions)
    if regression_drop_points is not None:
        row.regression_drop_points = float(regression_drop_points)
    row.updated_by = actor.id
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return get_policy(db, course_id)


def indicator_for_status(status: str) -> str:
    s = (status or "").upper()
    if s == "MASTERED":
        return "GREEN"
    if s in ("LEARNING", "READY_FOR_REASSESSMENT", "REASSESSMENT_PENDING"):
        return "YELLOW"
    if s == "NEEDS_PRACTICE":
        return "ORANGE"
    if s in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED"):
        return "RED"
    return "GRAY"


def _append_event(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
    event_type: str,
    from_status: Optional[str],
    to_status: Optional[str],
    attempt_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    evidence: Optional[Dict[str, Any]] = None,
    explanation: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(
        models.MasteryEvent(
            student_id=student_id,
            course_id=course_id,
            topic_id=topic_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            attempt_id=attempt_id,
            assessment_id=assessment_id,
            evidence=evidence,
            explanation=explanation,
        )
    )


def _get_or_create_state(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> models.TopicMasteryState:
    row = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
            models.TopicMasteryState.topic_id == topic_id,
        )
        .first()
    )
    if row:
        return row
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise _http(404, "Topic not found")
    row = models.TopicMasteryState(
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
        subject_id=topic.subject_id,
        status="NOT_ASSESSED",
        indicator="GRAY",
        target_difficulty="EASY",
        eligibility_flags={},
        explanation={"note": "Initialized"},
    )
    db.add(row)
    db.flush()
    return row


def _topic_attempt_stats(
    db: Session, attempt: models.AssessmentAttempt, topic_id: int
) -> Dict[str, Any]:
    records = (
        db.query(models.PerformanceRecord)
        .filter(
            models.PerformanceRecord.attempt_id == attempt.id,
            models.PerformanceRecord.topic_id == topic_id,
        )
        .all()
    )
    if not records:
        # Fall back to overall attempt if assessment is topic-scoped
        pct = float(attempt.percentage) if attempt.percentage is not None else None
        qn = (
            (attempt.correct_count or 0)
            + (attempt.incorrect_count or 0)
            + (attempt.unanswered_count or 0)
        )
        if not qn and getattr(attempt, "version", None) is not None:
            qn = int(attempt.version.total_questions or 0)
        return {
            "questions": qn,
            "correct": attempt.correct_count,
            "incorrect": attempt.incorrect_count,
            "percentage": pct,
            "accuracy": (pct / 100.0) if pct is not None else None,
            "source": "attempt_overall",
        }
    n = len(records)
    correct = sum(1 for r in records if r.is_correct)
    incorrect = sum(1 for r in records if r.is_incorrect)
    obtained = sum(float(r.marks_obtained or 0) for r in records)
    available = sum(float(r.marks_available or 0) for r in records)
    pct = round(100.0 * obtained / available, 2) if available else None
    return {
        "questions": n,
        "correct": correct,
        "incorrect": incorrect,
        "percentage": pct,
        "accuracy": round(correct / n, 4) if n else None,
        "source": "performance_records",
    }


def evaluate_mastery_decision(
    *,
    percentage: Optional[float],
    questions: int,
    correct: Optional[int],
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic mastery evaluator (no LLM)."""
    thr = float(policy["mastery_threshold"])
    min_q = int(policy["min_reassessment_questions"])
    reasons = []
    if percentage is None:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "mastered": False,
            "explanation": {
                "summary": "No percentage available for mastery evaluation",
                "reasons": ["Missing score evidence"],
            },
        }
    if questions < min_q:
        reasons.append(f"Question count {questions} < min_reassessment_questions {min_q}")
    if percentage >= thr:
        reasons.append(f"Reassessment score {percentage}% >= mastery threshold {thr}%")
        if correct is not None:
            reasons.append(f"Correct answers: {correct}/{questions}")
        if questions < min_q:
            return {
                "decision": "INSUFFICIENT_EVIDENCE",
                "mastered": False,
                "explanation": {
                    "summary": f"Score {percentage}% meets threshold but evidence volume is insufficient",
                    "reasons": reasons,
                    "mastery_threshold": thr,
                    "score": percentage,
                },
            }
        return {
            "decision": "MASTERED",
            "mastered": True,
            "explanation": {
                "summary": f"Topic mastered: score {percentage}% meets threshold {thr}%",
                "reasons": reasons,
                "mastery_threshold": thr,
                "score": percentage,
                "questions": questions,
                "correct": correct,
            },
        }
    reasons.append(f"Reassessment score {percentage}% < mastery threshold {thr}%")
    return {
        "decision": "GAP_PERSISTS",
        "mastered": False,
        "explanation": {
            "summary": f"Mastery not achieved: {percentage}% below {thr}%",
            "reasons": reasons,
            "mastery_threshold": thr,
            "score": percentage,
            "questions": questions,
            "correct": correct,
            "next_action": "ADAPTIVE_PRACTICE_OR_REMEDIATION",
        },
    }


def next_difficulty(current: str, *, accuracy_pct: float, practice_threshold: float) -> Tuple[str, str]:
    order = ["EASY", "MEDIUM", "HARD", "ADVANCED"]
    cur = (current or "EASY").upper()
    if cur not in order:
        cur = "EASY"
    idx = order.index(cur)
    if accuracy_pct >= practice_threshold + 10 and idx < len(order) - 1:
        return order[idx + 1], f"Accuracy {accuracy_pct}% strong → increase difficulty"
    if accuracy_pct < practice_threshold - 15 and idx > 0:
        return order[idx - 1], f"Accuracy {accuracy_pct}% weak → reduce difficulty"
    if accuracy_pct < practice_threshold and idx > 0:
        return order[max(0, idx - 1)], f"Accuracy {accuracy_pct}% below practice threshold → reinforce"
    return cur, f"Accuracy {accuracy_pct}% → maintain difficulty {cur}"


def sync_states_from_gaps(
    db: Session,
    *,
    student_id: int,
    course_id: int,
) -> List[models.TopicMasteryState]:
    """Seed/update mastery states from P0-012 learning gaps + topic performance (no score duplication)."""
    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
            models.LearningGap.scope_type == "TOPIC",
        )
        .all()
    )
    updated = []
    for g in gaps:
        if not g.scope_id:
            continue
        state = _get_or_create_state(
            db, student_id=student_id, course_id=course_id, topic_id=g.scope_id
        )
        if state.status in ("MASTERED", "READY_FOR_REASSESSMENT", "REASSESSMENT_PENDING"):
            updated.append(state)
            continue
        prev = state.status
        if g.classification in ("WEAK", "CRITICAL_GAP"):
            state.status = "NEEDS_REMEDIATION"
        elif g.classification == "DEVELOPING":
            state.status = "NEEDS_PRACTICE"
        else:
            state.status = "LEARNING"
        state.indicator = indicator_for_status(state.status)
        state.explanation = {
            "summary": f"Synced from P0-012 gap classification={g.classification}",
            "gap_id": g.id,
            "classification": g.classification,
        }
        if prev != state.status:
            _append_event(
                db,
                student_id=student_id,
                course_id=course_id,
                topic_id=g.scope_id,
                event_type="SYNCED_FROM_GAP",
                from_status=prev,
                to_status=state.status,
                explanation=state.explanation,
            )
        updated.append(state)
    db.commit()
    return updated


def _update_learning_profile_mastery(
    db: Session, student_id: int, course_id: int
) -> None:
    pref = (
        db.query(models.StudentLearningProfile)
        .filter(
            models.StudentLearningProfile.student_id == student_id,
            models.StudentLearningProfile.course_id == course_id,
        )
        .first()
    )
    states = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
        )
        .all()
    )
    topics = {t.id: t for t in db.query(models.Topic).filter(models.Topic.id.in_([s.topic_id for s in states] or [-1])).all()}
    block = {
        "mastered_topics": [
            {"topic_id": s.topic_id, "name": getattr(topics.get(s.topic_id), "name", None), "percent": s.mastery_percent}
            for s in states
            if s.status == "MASTERED"
        ],
        "weak_topics": [
            {"topic_id": s.topic_id, "name": getattr(topics.get(s.topic_id), "name", None), "status": s.status, "indicator": s.indicator}
            for s in states
            if s.status in ("NEEDS_REMEDIATION", "NEEDS_PRACTICE", "MASTERY_REGRESSED")
        ],
        "improving_topics": [
            {"topic_id": s.topic_id, "name": getattr(topics.get(s.topic_id), "name", None), "status": s.status}
            for s in states
            if s.status in ("LEARNING", "READY_FOR_REASSESSMENT", "REMEDIATION_IN_PROGRESS")
        ],
        "persistent_gaps": [
            {"topic_id": s.topic_id, "name": getattr(topics.get(s.topic_id), "name", None)}
            for s in states
            if s.status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED")
        ],
        "recent_reassessments": [
            {
                "topic_id": s.topic_id,
                "attempt_id": s.last_reassessment_attempt_id,
                "percent": s.mastery_percent,
                "status": s.status,
            }
            for s in states
            if s.last_reassessment_attempt_id
        ],
        "updated_at": _utcnow().isoformat(),
    }
    if not pref:
        pref = models.StudentLearningProfile(
            student_id=student_id,
            course_id=course_id,
            profile_json={"mastery": block},
        )
        db.add(pref)
    else:
        profile = dict(pref.profile_json or {})
        profile["mastery"] = block
        pref.profile_json = profile
        pref.generated_at = _utcnow()
    db.commit()


def list_mastery(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    sync: bool = True,
) -> Dict[str, Any]:
    _authorize_view(db, actor, student_id, course_id)
    if sync:
        sync_states_from_gaps(db, student_id=student_id, course_id=course_id)
    rows = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
        )
        .order_by(models.TopicMasteryState.topic_id)
        .all()
    )
    topics = {
        t.id: t
        for t in db.query(models.Topic)
        .filter(models.Topic.id.in_([r.topic_id for r in rows] or [-1]))
        .all()
    }
    policy = get_policy(db, course_id)
    return {
        "student_id": student_id,
        "course_id": course_id,
        "policy": policy,
        "topics": [state_to_dict(r, topic=topics.get(r.topic_id)) for r in rows],
    }


def get_topic_mastery(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    _authorize_view(db, actor, student_id, course_id)
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    db.commit()
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    events = (
        db.query(models.MasteryEvent)
        .filter(
            models.MasteryEvent.student_id == student_id,
            models.MasteryEvent.course_id == course_id,
            models.MasteryEvent.topic_id == topic_id,
        )
        .order_by(models.MasteryEvent.id.desc())
        .limit(50)
        .all()
    )
    return {
        **state_to_dict(state, topic=topic),
        "policy": get_policy(db, course_id),
        "history": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "evidence": e.evidence,
                "explanation": e.explanation,
                "attempt_id": e.attempt_id,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


def recommend_practice(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    _authorize_self_or_staff(db, actor, student_id, course_id)
    policy = get_policy(db, course_id)
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise _http(404, "Topic not found")
    difficulty = state.target_difficulty or "EASY"
    # Prefer foundational difficulty for remediation needs
    if state.status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED") and difficulty in ("HARD", "ADVANCED"):
        difficulty = "EASY"
    reasons = [
        f"Topic = {topic.name}",
        f"Current mastery status = {state.status}",
        f"Target difficulty = {difficulty}",
        f"Practice threshold = {policy['practice_threshold']}%",
    ]
    if state.practice_accuracy is not None:
        reasons.append(f"Recent practice accuracy = {state.practice_accuracy}%")
    recommendation = {
        "topic_id": topic_id,
        "topic_name": topic.name,
        "difficulty": difficulty,
        "question_count": max(3, min(8, int(policy["min_reassessment_questions"]))),
        "why_selected": reasons,
        "adaptive_rule": "Foundational practice for gaps; increase difficulty after consistent success",
    }
    _append_event(
        db,
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
        event_type="PRACTICE_RECOMMENDED",
        from_status=state.status,
        to_status=state.status,
        explanation=recommendation,
    )
    db.commit()
    notif_svc.emit_event(
        db,
        event="PRACTICE_RECOMMENDED",
        title=f"Practice recommended: {topic.name}",
        message=f"Adaptive practice at {difficulty} difficulty is recommended for {topic.name}.",
        student_id=student_id,
        course_id=course_id,
        source_module="MASTERY",
        link_path="/mastery/me",
        payload=recommendation,
        channels=["IN_APP", "EMAIL"],
    )
    return recommendation


def _creator_for_course(db: Session, course_id: int, fallback: models.User) -> models.User:
    coord = (
        db.query(models.User)
        .join(
            models.FacultyCourseAssignment,
            models.FacultyCourseAssignment.faculty_id == models.User.id,
        )
        .filter(models.FacultyCourseAssignment.course_id == course_id)
        .first()
    )
    if coord:
        return coord
    admin = db.query(models.User).filter(
        models.User.role.in_(roles.ADMIN_PERMISSION_ROLES),
        models.User.is_active.is_(True),
    ).first()
    return admin or fallback


def _publish_topic_assessment(
    db: Session,
    *,
    creator: models.User,
    course_id: int,
    subject_id: int,
    topic_id: int,
    title: str,
    assessment_type: str,
    difficulty: str,
    question_count: int,
    exclude_question_ids: Optional[set] = None,
) -> models.Assessment:
    exclude_question_ids = exclude_question_ids or set()
    marks_each = 1.0
    a = models.Assessment(
        title=title,
        course_id=course_id,
        created_by=creator.id,
        category="TOPIC_MASTERY",
        assessment_type=assessment_type,
        status="DRAFT",
        duration_minutes=max(10, question_count * 3),
        total_questions=question_count,
        total_marks=question_count * marks_each,
        marks_correct=marks_each,
        marks_incorrect=0.0,
        marks_unanswered=0.0,
        subject_id=subject_id,
        topic_id=topic_id,
        max_attempts=1,
        available_from=_utcnow(),
    )
    db.add(a)
    db.flush()
    db.add(
        models.AssessmentBlueprintItem(
            assessment_id=a.id,
            subject_id=subject_id,
            topic_id=topic_id,
            difficulty=difficulty if difficulty in DIFFICULTIES else "EASY",
            question_count=question_count,
        )
    )
    db.flush()
    a = db.query(models.Assessment).filter(models.Assessment.id == a.id).first()
    items = list(a.blueprint_items)
    selected, errors = aeng.assemble_questions(db, a, items)
    # Prefer novelty: drop previously seen if alternatives exist
    if exclude_question_ids:
        filtered = [q for q in selected if q.id not in exclude_question_ids]
        if len(filtered) >= max(1, question_count // 2):
            # top-up from selection engine if needed
            if len(filtered) < question_count:
                extra = sel.select_questions(
                    db,
                    course_id=course_id,
                    total_questions=question_count,
                    subject_distribution={subject_id: question_count},
                    topic_ids=[topic_id],
                    difficulty_distribution={difficulty: question_count},
                    reuse_policy="NOVEL",
                    evidence_based=True,
                )
                for q in extra.get("questions") or []:
                    if q.id in exclude_question_ids or any(x.id == q.id for x in filtered):
                        continue
                    filtered.append(q)
                    if len(filtered) >= question_count:
                        break
            selected = filtered[:question_count]
    # Blueprint assemble may fail on a single difficulty; always try cross-difficulty top-up
    # before hard-failing (adaptive practice must not require a full pool at one level).
    if len(selected) < question_count:
        for d in DIFFICULTIES:
            if d == difficulty and selected:
                continue
            need = question_count - len(selected)
            if need <= 0:
                break
            extra = sel.select_questions(
                db,
                course_id=course_id,
                total_questions=need,
                subject_distribution={subject_id: need},
                topic_ids=[topic_id],
                difficulty_distribution={d: need},
                reuse_policy="MIXED",
                evidence_based=True,
            )
            for q in extra.get("questions") or []:
                if any(x.id == q.id for x in selected):
                    continue
                if exclude_question_ids and q.id in exclude_question_ids and len(selected) >= max(1, question_count // 2):
                    continue
                selected.append(q)
                if len(selected) >= question_count:
                    break
            if len(selected) >= question_count:
                break
    if not selected:
        detail = f"Unable to assemble practice questions: {errors}" if errors else "No eligible questions available for this topic"
        raise _http(422, detail)

    a.total_questions = len(selected)
    a.total_marks = len(selected) * marks_each
    version = models.AssessmentVersion(
        assessment_id=a.id,
        version_number=1,
        blueprint_snapshot=[
            {
                "subject_id": subject_id,
                "topic_id": topic_id,
                "difficulty": difficulty,
                "question_count": len(selected),
            }
        ],
        marking_snapshot={
            "marks_correct": marks_each,
            "marks_incorrect": 0.0,
            "marks_unanswered": 0.0,
        },
        duration_minutes=a.duration_minutes,
        total_questions=len(selected),
        total_marks=a.total_marks,
        category=a.category,
        assessment_type=a.assessment_type,
        published_by=creator.id,
    )
    db.add(version)
    db.flush()
    for i, q in enumerate(selected, start=1):
        db.add(
            models.AssessmentQuestion(
                version_id=version.id,
                question_id=q.id,
                sequence=i,
                subject_id=q.subject_id,
                topic_id=q.topic_id,
                subtopic_id=q.subtopic_id,
                difficulty=q.difficulty,
                marks_available=marks_each,
                stem_snapshot=q.stem,
                options_snapshot=q.options,
                correct_answer_snapshot=q.correct_answer,
                explanation_snapshot=q.explanation,
                question_type_snapshot=q.question_type,
            )
        )
    a.status = "PUBLISHED"
    db.commit()
    db.refresh(a)
    return a


def _prior_question_ids(db: Session, student_id: int, topic_id: int) -> set:
    rows = (
        db.query(models.PerformanceRecord.question_id)
        .filter(
            models.PerformanceRecord.student_id == student_id,
            models.PerformanceRecord.topic_id == topic_id,
        )
        .all()
    )
    return {r[0] for r in rows if r[0]}


def start_practice(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    _authorize_self_or_staff(db, actor, student_id, course_id)
    rec = recommend_practice(db, actor, student_id=student_id, course_id=course_id, topic_id=topic_id)
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    creator = _creator_for_course(db, course_id, actor)
    assessment = _publish_topic_assessment(
        db,
        creator=creator,
        course_id=course_id,
        subject_id=topic.subject_id,
        topic_id=topic_id,
        title=f"Adaptive Practice — {topic.name}",
        assessment_type="ADAPTIVE_PRACTICE",
        difficulty=rec["difficulty"],
        question_count=rec["question_count"],
        exclude_question_ids=_prior_question_ids(db, student_id, topic_id),
    )
    assignment = models.AdaptivePracticeAssignment(
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
        purpose="PRACTICE",
        assessment_id=assessment.id,
        difficulty=rec["difficulty"],
        status="READY",
        recommendation=rec,
    )
    db.add(assignment)
    if state.status in ("NEEDS_REMEDIATION", "NOT_ASSESSED", "MASTERY_REGRESSED"):
        prev = state.status
        state.status = "NEEDS_PRACTICE" if state.status != "NEEDS_REMEDIATION" else state.status
        if prev == "NEEDS_REMEDIATION":
            pass
        state.indicator = indicator_for_status(state.status)
    db.commit()
    db.refresh(assignment)
    return {
        "assignment_id": assignment.id,
        "assessment_id": assessment.id,
        "purpose": "PRACTICE",
        "difficulty": rec["difficulty"],
        "recommendation": rec,
        "start_path": f"/student/assessments/{assessment.id}/start",
        "mastery": state_to_dict(state, topic=topic),
    }


def check_reassessment_eligibility(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    _authorize_view(db, actor, student_id, course_id)
    policy = get_policy(db, course_id)
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    flags = dict(state.eligibility_flags or {})
    reasons = []
    eligible = False

    practice_ok = (
        state.practice_accuracy is not None
        and float(state.practice_accuracy) >= float(policy["reassessment_threshold"])
    )
    if practice_ok:
        eligible = True
        reasons.append(
            f"Practice accuracy {state.practice_accuracy}% >= reassessment threshold "
            f"{policy['reassessment_threshold']}%"
        )
        flags["practice_ready"] = True

    # Optional P0-014 completion — never required alone for eligibility
    interventions = (
        db.query(models.RemedialIntervention)
        .filter(
            models.RemedialIntervention.course_id == course_id,
            models.RemedialIntervention.status.in_(("COMPLETED", "EVALUATED")),
        )
        .all()
    )
    member_gids = {
        m.group_id
        for m in db.query(models.RemedialGroupMember)
        .filter(
            models.RemedialGroupMember.student_id == student_id,
            models.RemedialGroupMember.status != "REMOVED",
        )
        .all()
    }
    topic_interventions = []
    for i in interventions:
        if i.student_id == student_id or (i.group_id and i.group_id in member_gids):
            snap = i.gap_snapshot or {}
            if snap.get("scope_id") == topic_id or (snap.get("scope_type") or "").upper() == "TOPIC":
                topic_interventions.append(i)
    if topic_interventions:
        flags["intervention_completed"] = True
        reasons.append("P0-014 remedial intervention completed (optional pathway signal)")

    if flags.get("self_reported_ready"):
        eligible = True
        reasons.append(
            f"Student declared ready via remediation_source={state.remediation_source or 'UNKNOWN'}"
        )
    if flags.get("faculty_approved"):
        eligible = True
        reasons.append("Faculty approved reassessment eligibility")

    # Any declared remediation source enables self-study path without SYS remediation
    if state.remediation_source and flags.get("self_reported_ready"):
        eligible = True

    if state.status == "MASTERED":
        eligible = False
        reasons = ["Topic already MASTERED — reassessment not required"]

    state.eligibility_flags = flags
    if eligible and state.status not in ("REASSESSMENT_PENDING", "MASTERED"):
        prev = state.status
        state.status = "READY_FOR_REASSESSMENT"
        state.indicator = indicator_for_status(state.status)
        if prev != state.status:
            _append_event(
                db,
                student_id=student_id,
                course_id=course_id,
                topic_id=topic_id,
                event_type="REASSESSMENT_ELIGIBLE",
                from_status=prev,
                to_status=state.status,
                explanation={"reasons": reasons, "flags": flags},
            )
    db.commit()
    return {
        "eligible": eligible,
        "status": state.status,
        "reasons": reasons,
        "flags": flags,
        "policy": policy,
        "note": "SYS remediation completion is optional; self-study/human-expert pathways are valid.",
    }


def declare_ready(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
    remediation_source: str = "SELF_STUDY",
) -> Dict[str, Any]:
    """Self-study / human-expert / classroom pathway — does NOT require P0-014."""
    _authorize_self_or_staff(db, actor, student_id, course_id)
    source = (remediation_source or "SELF_STUDY").upper()
    if source not in REMEDIATION_SOURCES:
        raise _http(422, f"Invalid remediation_source: {source}")
    # Source is context only — must not alter mastery thresholds
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    state.remediation_source = source
    flags = dict(state.eligibility_flags or {})
    flags["self_reported_ready"] = True
    if source == "AI_LECTURER":
        flags["ai_lecturer_path"] = True
    elif source == "HUMAN_EXPERT":
        flags["human_expert_path"] = True
    elif source == "SELF_STUDY":
        flags["self_study_path"] = True
    state.eligibility_flags = flags
    if state.status in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS"):
        state.status = "REMEDIATION_IN_PROGRESS"
        state.indicator = indicator_for_status(state.status)
    db.commit()
    return check_reassessment_eligibility(
        db, actor, student_id=student_id, course_id=course_id, topic_id=topic_id
    )


def faculty_approve_reassessment(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    if not can_manage_learning_sessions(db, actor, course_id=course_id):
        raise _http(403, "Not authorized")
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    flags = dict(state.eligibility_flags or {})
    flags["faculty_approved"] = True
    state.eligibility_flags = flags
    db.commit()
    return check_reassessment_eligibility(
        db, actor, student_id=student_id, course_id=course_id, topic_id=topic_id
    )


def start_reassessment(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    _authorize_self_or_staff(db, actor, student_id, course_id)
    elig = check_reassessment_eligibility(
        db, actor, student_id=student_id, course_id=course_id, topic_id=topic_id
    )
    if not elig["eligible"]:
        raise _http(422, "Not eligible for reassessment: " + "; ".join(elig.get("reasons") or []))
    policy = get_policy(db, course_id)
    state = _get_or_create_state(db, student_id=student_id, course_id=course_id, topic_id=topic_id)
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    creator = _creator_for_course(db, course_id, actor)
    qcount = max(int(policy["min_reassessment_questions"]), 5)
    # Reassessment uses mixed/moderate+ difficulty, avoid prior questions
    diff = "MEDIUM" if state.target_difficulty in ("EASY", "MEDIUM") else state.target_difficulty
    assessment = _publish_topic_assessment(
        db,
        creator=creator,
        course_id=course_id,
        subject_id=topic.subject_id,
        topic_id=topic_id,
        title=f"Topic Reassessment — {topic.name}",
        assessment_type="TOPIC_REASSESSMENT",
        difficulty=diff,
        question_count=qcount,
        exclude_question_ids=_prior_question_ids(db, student_id, topic_id),
    )
    assignment = models.AdaptivePracticeAssignment(
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
        purpose="REASSESSMENT",
        assessment_id=assessment.id,
        difficulty=diff,
        status="READY",
        recommendation={"eligibility": elig, "why": "Eligible reassessment targeting unresolved topic"},
    )
    db.add(assignment)
    prev = state.status
    state.status = "REASSESSMENT_PENDING"
    state.indicator = indicator_for_status(state.status)
    _append_event(
        db,
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
        event_type="REASSESSMENT_STARTED",
        from_status=prev,
        to_status=state.status,
        assessment_id=assessment.id,
        explanation={"remediation_source": state.remediation_source, "eligibility": elig},
    )
    db.commit()
    db.refresh(assignment)
    notif_svc.emit_event(
        db,
        event="REASSESSMENT_AVAILABLE",
        title=f"Reassessment available: {topic.name}",
        message="A topic reassessment is ready. Mastery requires demonstrated competence — not remediation completion alone.",
        student_id=student_id,
        course_id=course_id,
        assessment_id=assessment.id,
        source_module="MASTERY",
        link_path=f"/student/assessments/{assessment.id}/start",
        payload={"assessment_id": assessment.id, "topic_id": topic_id},
        channels=["IN_APP", "EMAIL"],
    )
    return {
        "assignment_id": assignment.id,
        "assessment_id": assessment.id,
        "purpose": "REASSESSMENT",
        "start_path": f"/student/assessments/{assessment.id}/start",
        "eligibility": elig,
        "mastery": state_to_dict(state, topic=topic),
    }


def process_attempt_for_mastery(db: Session, attempt: models.AssessmentAttempt) -> Dict[str, Any]:
    """Hook after P0-011 evaluation / P0-012 analysis. Does not overwrite historical records."""
    a = attempt.assessment
    if not a:
        return {}
    purpose = None
    topic_id = a.topic_id
    assignment = (
        db.query(models.AdaptivePracticeAssignment)
        .filter(models.AdaptivePracticeAssignment.assessment_id == a.id)
        .first()
    )
    if assignment:
        purpose = assignment.purpose
        topic_id = assignment.topic_id
        assignment.status = "COMPLETED"
        assignment.completed_attempt_id = attempt.id
    if not topic_id:
        return {}

    policy = get_policy(db, attempt.course_id)
    state = _get_or_create_state(
        db,
        student_id=attempt.student_id,
        course_id=attempt.course_id,
        topic_id=topic_id,
    )
    stats = _topic_attempt_stats(db, attempt, topic_id)
    pct = stats.get("percentage")
    results: Dict[str, Any] = {"purpose": purpose or a.assessment_type, "stats": stats}

    if purpose == "PRACTICE" or a.assessment_type == "ADAPTIVE_PRACTICE":
        acc_pct = float(pct) if pct is not None else 0.0
        state.practice_accuracy = acc_pct
        state.last_practice_attempt_id = attempt.id
        new_diff, rule = next_difficulty(
            state.target_difficulty,
            accuracy_pct=acc_pct,
            practice_threshold=float(policy["practice_threshold"]),
        )
        state.target_difficulty = new_diff
        prev = state.status
        if acc_pct >= float(policy["reassessment_threshold"]):
            state.status = "READY_FOR_REASSESSMENT"
            flags = dict(state.eligibility_flags or {})
            flags["practice_ready"] = True
            state.eligibility_flags = flags
        elif acc_pct < float(policy["practice_threshold"]):
            state.status = "NEEDS_PRACTICE"
        else:
            state.status = "LEARNING"
        state.indicator = indicator_for_status(state.status)
        explanation = {
            "summary": f"Practice evaluated at {acc_pct}%",
            "adaptive_rule": rule,
            "target_difficulty": new_diff,
            "reasons": [
                f"Previous target difficulty adjusted by rule: {rule}",
                f"Practice threshold={policy['practice_threshold']}%",
                f"Reassessment threshold={policy['reassessment_threshold']}%",
            ],
        }
        state.explanation = explanation
        state.last_decision_at = _utcnow()
        _append_event(
            db,
            student_id=attempt.student_id,
            course_id=attempt.course_id,
            topic_id=topic_id,
            event_type="PRACTICE_EVALUATED",
            from_status=prev,
            to_status=state.status,
            attempt_id=attempt.id,
            assessment_id=a.id,
            evidence=stats,
            explanation=explanation,
        )
        db.commit()
        if state.status == "READY_FOR_REASSESSMENT":
            notif_svc.emit_event(
                db,
                event="REASSESSMENT_AVAILABLE",
                title="Ready for reassessment",
                message="Practice performance meets the reassessment readiness threshold.",
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                source_module="MASTERY",
                link_path="/mastery/me",
                payload={"topic_id": topic_id, "practice_accuracy": acc_pct},
                channels=["IN_APP", "EMAIL"],
            )
        results["mastery"] = state_to_dict(state)
        _update_learning_profile_mastery(db, attempt.student_id, attempt.course_id)
        return results

    if purpose == "REASSESSMENT" or a.assessment_type == "TOPIC_REASSESSMENT":
        decision = evaluate_mastery_decision(
            percentage=pct,
            questions=int(stats.get("questions") or 0),
            correct=stats.get("correct"),
            policy=policy,
        )
        prev = state.status
        state.last_reassessment_attempt_id = attempt.id
        state.mastery_percent = pct
        state.last_decision_at = _utcnow()
        state.explanation = decision["explanation"]
        # Remediation source must NOT affect decision
        decision["explanation"]["remediation_source_context"] = state.remediation_source
        decision["explanation"]["remediation_source_affects_decision"] = False

        if decision["mastered"]:
            state.status = "MASTERED"
            state.indicator = "GREEN"
            # Resolve matching learning gap interpretation without deleting history
            gaps = (
                db.query(models.LearningGap)
                .filter(
                    models.LearningGap.student_id == attempt.student_id,
                    models.LearningGap.course_id == attempt.course_id,
                    models.LearningGap.scope_type == "TOPIC",
                    models.LearningGap.scope_id == topic_id,
                )
                .all()
            )
            for g in gaps:
                inf = dict(g.inference or {})
                inf["mastery_status"] = "RESOLVED"
                inf["resolved_by_attempt_id"] = attempt.id
                g.inference = inf
            _append_event(
                db,
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                topic_id=topic_id,
                event_type="MASTERED",
                from_status=prev,
                to_status="MASTERED",
                attempt_id=attempt.id,
                assessment_id=a.id,
                evidence=stats,
                explanation=decision["explanation"],
            )
            db.commit()
            notif_svc.emit_event(
                db,
                event="TOPIC_MASTERED",
                title="Topic mastered",
                message=decision["explanation"]["summary"],
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                assessment_id=a.id,
                severity="SUCCESS",
                source_module="MASTERY",
                link_path="/mastery/me",
                payload={"topic_id": topic_id, "decision": decision},
                channels=["IN_APP", "EMAIL"],
            )
        else:
            state.status = "NEEDS_REMEDIATION"
            state.indicator = "RED"
            _append_event(
                db,
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                topic_id=topic_id,
                event_type="REASSESSMENT_FAILED",
                from_status=prev,
                to_status=state.status,
                attempt_id=attempt.id,
                assessment_id=a.id,
                evidence=stats,
                explanation=decision["explanation"],
            )
            db.commit()
            notif_svc.emit_event(
                db,
                event="FURTHER_REMEDIATION_RECOMMENDED",
                title="Further practice/remediation recommended",
                message=decision["explanation"]["summary"],
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                severity="WARNING",
                source_module="MASTERY",
                link_path="/mastery/me",
                payload={"topic_id": topic_id, "decision": decision},
                channels=["IN_APP", "EMAIL"],
            )
        notif_svc.emit_event(
            db,
            event="REASSESSMENT_COMPLETED",
            title="Reassessment completed",
            message=f"Reassessment scored {pct}%. Decision: {decision['decision']}.",
            student_id=attempt.student_id,
            course_id=attempt.course_id,
            assessment_id=a.id,
            source_module="MASTERY",
            link_path=f"/student/attempts/{attempt.id}/result",
            payload={"decision": decision, "topic_id": topic_id},
            channels=["IN_APP", "EMAIL"],
        )
        results["decision"] = decision
        results["mastery"] = state_to_dict(state)
        _update_learning_profile_mastery(db, attempt.student_id, attempt.course_id)
        return results

    # General assessments: conservative regression check for MASTERED topics
    if state.status == "MASTERED" and pct is not None:
        thr = float(policy["mastery_threshold"])
        drop = float(policy["regression_drop_points"])
        if pct <= thr - drop and int(stats.get("questions") or 0) >= int(policy["min_reassessment_questions"]):
            prev = state.status
            state.status = "MASTERY_REGRESSED"
            state.indicator = "RED"
            state.mastery_percent = pct
            explanation = {
                "summary": (
                    f"Conservative regression: score {pct}% is >= {drop} points below "
                    f"mastery threshold {thr}% on sufficient evidence"
                ),
                "reasons": [
                    "Single minor mistakes do not trigger regression",
                    f"Required drop: {drop} points below {thr}%",
                    f"Observed score: {pct}%",
                ],
            }
            state.explanation = explanation
            _append_event(
                db,
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                topic_id=topic_id,
                event_type="MASTERY_REGRESSED",
                from_status=prev,
                to_status=state.status,
                attempt_id=attempt.id,
                assessment_id=a.id,
                evidence=stats,
                explanation=explanation,
            )
            db.commit()
            notif_svc.emit_event(
                db,
                event="MASTERY_REGRESSION_DETECTED",
                title="Mastery regression detected",
                message=explanation["summary"],
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                severity="WARNING",
                source_module="MASTERY",
                link_path="/mastery/me",
                payload={"topic_id": topic_id},
                channels=["IN_APP", "EMAIL"],
            )
            _update_learning_profile_mastery(db, attempt.student_id, attempt.course_id)
            results["decision"] = {"decision": "MASTERY_REGRESSED", "explanation": explanation}
    return results


def state_to_dict(
    state: models.TopicMasteryState,
    *,
    topic: Optional[models.Topic] = None,
) -> Dict[str, Any]:
    return {
        "id": state.id,
        "student_id": state.student_id,
        "course_id": state.course_id,
        "topic_id": state.topic_id,
        "topic_name": topic.name if topic else None,
        "subject_id": state.subject_id,
        "status": state.status,
        "indicator": state.indicator,
        "mastery_percent": state.mastery_percent,
        "practice_accuracy": state.practice_accuracy,
        "target_difficulty": state.target_difficulty,
        "remediation_source": state.remediation_source,
        "eligibility_flags": state.eligibility_flags,
        "explanation": state.explanation,
        "last_practice_attempt_id": state.last_practice_attempt_id,
        "last_reassessment_attempt_id": state.last_reassessment_attempt_id,
        "last_decision_at": state.last_decision_at,
        "updated_at": state.updated_at,
    }
