"""P0-016 Learning Intelligence — aggregation over P0-010..015 authoritative data.

Does NOT recalculate mastery, performance, or learning gaps.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.academic_auth import can_access_course_questions, get_coordinated_course_ids, is_admin
from app.services import early_warning as ew
from app.services import mastery_engine as mastery
from app.services import notifications as notif_svc


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _authorize_student_view(db: Session, actor: models.User, student_id: int, course_id: int) -> None:
    if not notif_svc.user_can_view_student_performance(db, actor, student_id, course_id):
        raise _http(403, "Not authorized for this student/course analytics")


def _authorize_faculty_course(db: Session, actor: models.User, course_id: int) -> None:
    role = (actor.role or "").lower()
    if role == "student":
        raise _http(403, "Faculty or admin access required")
    if is_admin(actor):
        return
    if can_access_course_questions(db, actor, course_id):
        return
    raise _http(403, "Not authorized for this course analytics")


def _authorize_admin(actor: models.User) -> None:
    if not is_admin(actor):
        raise _http(403, "Admin access required")


def _gap_resolved(gap: models.LearningGap) -> bool:
    return str((gap.inference or {}).get("mastery_status") or "").upper() == "RESOLVED"


def _topic_map(db: Session, topic_ids: Set[int]) -> Dict[int, models.Topic]:
    if not topic_ids:
        return {}
    rows = db.query(models.Topic).filter(models.Topic.id.in_(list(topic_ids))).all()
    return {t.id: t for t in rows}


def _consistency_label(events: List[models.MasteryEvent], state: models.TopicMasteryState) -> str:
    """Explainable learning-consistency pattern (no single-score risk label)."""
    if state.status == "MASTERED":
        if any(e.event_type == "MASTERY_REGRESSED" for e in events):
            return "IMPROVEMENT_THEN_REGRESSION"
        return "CONSISTENTLY_STRONG"
    statuses = [e.to_status for e in events if e.to_status]
    if state.status == "MASTERY_REGRESSED":
        return "REGRESSED"
    fail_n = sum(1 for e in events if e.event_type == "REASSESSMENT_FAILED")
    if fail_n >= 2 or state.status in ("NEEDS_REMEDIATION",):
        return "PERSISTENT_WEAKNESS"
    practice_pcts = [
        float(e.evidence["percentage"])
        for e in events
        if e.event_type == "PRACTICE_EVALUATED" and (e.evidence or {}).get("percentage") is not None
    ]
    if len(practice_pcts) >= 2:
        if practice_pcts[-1] > practice_pcts[0] + 5:
            return "IMPROVING"
        if abs(practice_pcts[-1] - practice_pcts[0]) <= 5 and max(practice_pcts) - min(practice_pcts) > 15:
            return "UNSTABLE"
        if practice_pcts[-1] < practice_pcts[0] - 5:
            return "DECLINING"
    if state.status in ("LEARNING", "READY_FOR_REASSESSMENT", "NEEDS_PRACTICE"):
        return "IMPROVING" if state.status != "NEEDS_PRACTICE" else "DEVELOPING"
    if len(set(statuses)) >= 3:
        return "UNSTABLE"
    return "INSUFFICIENT_EVIDENCE"


def student_analytics(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
) -> Dict[str, Any]:
    _authorize_student_view(db, actor, student_id, course_id)
    policy = mastery.get_policy(db, course_id)
    warn_policy = ew.get_warning_policy(db, course_id)

    states = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
        )
        .all()
    )
    topics = _topic_map(db, {s.topic_id for s in states})
    events = (
        db.query(models.MasteryEvent)
        .filter(
            models.MasteryEvent.student_id == student_id,
            models.MasteryEvent.course_id == course_id,
        )
        .order_by(models.MasteryEvent.created_at.asc())
        .all()
    )
    events_by_topic: Dict[int, List[models.MasteryEvent]] = defaultdict(list)
    for e in events:
        events_by_topic[e.topic_id].append(e)

    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
        )
        .all()
    )
    active_gaps = [g for g in gaps if not _gap_resolved(g) and g.classification in ("WEAK", "CRITICAL_GAP", "DEVELOPING")]
    resolved_gaps = [g for g in gaps if _gap_resolved(g)]

    assignments = (
        db.query(models.AdaptivePracticeAssignment)
        .filter(
            models.AdaptivePracticeAssignment.student_id == student_id,
            models.AdaptivePracticeAssignment.course_id == course_id,
        )
        .order_by(models.AdaptivePracticeAssignment.created_at.desc())
        .all()
    )

    mastered, improving, needs_practice, needs_support = [], [], [], []
    topic_rows = []
    for s in states:
        t = topics.get(s.topic_id)
        evs = events_by_topic.get(s.topic_id, [])
        prev = None
        for e in reversed(evs):
            if e.from_status and e.to_status and e.to_status == s.status:
                prev = e.from_status
                break
        trend = _consistency_label(evs, s)
        practice_series = [
            float(e.evidence["percentage"])
            for e in evs
            if e.event_type == "PRACTICE_EVALUATED" and (e.evidence or {}).get("percentage") is not None
        ]
        has_persist = any(
            g.scope_type == "TOPIC" and g.scope_id == s.topic_id and not _gap_resolved(g) for g in active_gaps
        )
        rec = ew.recommend_for_status(s.status, has_persistent_gap=has_persist)
        row = {
            "topic_id": s.topic_id,
            "topic_name": t.name if t else f"Topic {s.topic_id}",
            "subject_id": s.subject_id,
            "status": s.status,
            "indicator": s.indicator,
            "mastery_percent": s.mastery_percent,
            "practice_accuracy": s.practice_accuracy,
            "target_difficulty": s.target_difficulty,
            "previous_status": prev,
            "trend": trend,
            "remediation_source": s.remediation_source,
            "last_decision_at": s.last_decision_at.isoformat() if s.last_decision_at else None,
            "practice_accuracy_series": practice_series,
            "recommendation": rec,
            "explanation": s.explanation,
            "source_of_truth": "P0-015_TopicMasteryState",
        }
        topic_rows.append(row)
        if s.status == "MASTERED":
            mastered.append(row)
        elif s.status in ("LEARNING", "READY_FOR_REASSESSMENT") or trend == "IMPROVING":
            improving.append(row)
        elif s.status == "NEEDS_PRACTICE":
            needs_practice.append(row)
        elif s.status in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED"):
            needs_support.append(row)

    warnings = ew.evaluate_student_warnings(
        db, student_id=student_id, course_id=course_id, policy=warn_policy
    )

    practice_asg = [a for a in assignments if a.purpose == "PRACTICE"]
    reass_asg = [a for a in assignments if a.purpose == "REASSESSMENT"]
    mastered_events = [e for e in events if e.event_type == "MASTERED"]
    failed_reass = [e for e in events if e.event_type == "REASSESSMENT_FAILED"]

    # Learning route analytics (contextual only)
    route_counter = Counter(
        (s.remediation_source or "UNKNOWN") for s in states if s.remediation_source
    )

    return {
        "student_id": student_id,
        "course_id": course_id,
        "policy": policy,
        "warning_policy": warn_policy,
        "summary": {
            "mastered_topics": len(mastered),
            "improving_topics": len(improving),
            "needs_practice": len(needs_practice),
            "needs_support": len(needs_support),
            "active_gaps": len(active_gaps),
            "resolved_gaps": len(resolved_gaps),
            "practice_assignments": len(practice_asg),
            "practice_completed": sum(1 for a in practice_asg if a.status == "COMPLETED"),
            "reassessments": len(reass_asg),
            "reassessments_completed": sum(1 for a in reass_asg if a.status == "COMPLETED"),
            "mastery_transitions": len(mastered_events),
            "reassessment_failures": len(failed_reass),
        },
        "mastered_topics": mastered,
        "improving_topics": improving,
        "needs_practice": needs_practice,
        "needs_support": needs_support,
        "topics": topic_rows,
        "gaps": {
            "active": [
                {
                    "id": g.id,
                    "scope_type": g.scope_type,
                    "scope_id": g.scope_id,
                    "scope_name": g.scope_name,
                    "classification": g.classification,
                    "priority_score": g.priority_score,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                    "resolved": False,
                }
                for g in active_gaps
            ],
            "resolved": [
                {
                    "id": g.id,
                    "scope_type": g.scope_type,
                    "scope_id": g.scope_id,
                    "scope_name": g.scope_name,
                    "classification": g.classification,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                    "resolved": True,
                    "inference": g.inference,
                }
                for g in resolved_gaps
            ],
        },
        "practice": {
            "assignments": [
                {
                    "id": a.id,
                    "topic_id": a.topic_id,
                    "difficulty": a.difficulty,
                    "status": a.status,
                    "assessment_id": a.assessment_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in practice_asg[:50]
            ],
        },
        "reassessment": {
            "assignments": [
                {
                    "id": a.id,
                    "topic_id": a.topic_id,
                    "status": a.status,
                    "assessment_id": a.assessment_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in reass_asg[:50]
            ],
            "mastered_count": len(mastered_events),
            "failed_count": len(failed_reass),
        },
        "learning_routes": {
            "usage": dict(route_counter),
            "note": "Remediation source is contextual evidence only and does not alter mastery decisions.",
        },
        "attention": warnings,
        "recommendations": [
            {
                "topic_id": r["topic_id"],
                "topic_name": r["topic_name"],
                "status": r["status"],
                **r["recommendation"],
            }
            for r in topic_rows
            if r["status"] != "NOT_ASSESSED"
        ],
        "recent_mastery_events": [
            {
                "id": e.id,
                "topic_id": e.topic_id,
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "explanation": e.explanation,
            }
            for e in sorted(events, key=lambda x: x.created_at or _utcnow(), reverse=True)[:30]
        ],
        "authority_note": "Mastery and gap facts come from P0-015 and P0-012; P0-016 aggregates only.",
    }


def student_trends(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    topic_id: Optional[int] = None,
) -> Dict[str, Any]:
    _authorize_student_view(db, actor, student_id, course_id)
    q = db.query(models.MasteryEvent).filter(
        models.MasteryEvent.student_id == student_id,
        models.MasteryEvent.course_id == course_id,
    )
    if topic_id is not None:
        q = q.filter(models.MasteryEvent.topic_id == topic_id)
    events = q.order_by(models.MasteryEvent.created_at.asc()).all()
    series = []
    for e in events:
        pct = None
        if e.evidence and e.evidence.get("percentage") is not None:
            pct = float(e.evidence["percentage"])
        series.append(
            {
                "at": e.created_at.isoformat() if e.created_at else None,
                "topic_id": e.topic_id,
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "percentage": pct,
            }
        )
    return {
        "student_id": student_id,
        "course_id": course_id,
        "topic_id": topic_id,
        "transitions": series,
        "note": "Historical values derived from append-only mastery events; none are fabricated.",
    }


def faculty_overview(db: Session, actor: models.User, *, course_id: int) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    enrollments = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.course_id == course_id)
        .all()
    )
    student_ids = [e.student_id for e in enrollments]
    states = (
        db.query(models.TopicMasteryState)
        .filter(models.TopicMasteryState.course_id == course_id)
        .all()
    )
    gaps = (
        db.query(models.LearningGap)
        .filter(models.LearningGap.course_id == course_id)
        .all()
    )
    active_gaps = [g for g in gaps if not _gap_resolved(g) and g.classification in ("WEAK", "CRITICAL_GAP", "DEVELOPING")]
    status_dist = Counter(s.status for s in states)
    interventions = (
        db.query(models.RemedialIntervention)
        .filter(models.RemedialIntervention.course_id == course_id)
        .all()
    )
    reass = (
        db.query(models.AdaptivePracticeAssignment)
        .filter(
            models.AdaptivePracticeAssignment.course_id == course_id,
            models.AdaptivePracticeAssignment.purpose == "REASSESSMENT",
        )
        .all()
    )
    mastered_ev = (
        db.query(models.MasteryEvent)
        .filter(
            models.MasteryEvent.course_id == course_id,
            models.MasteryEvent.event_type == "MASTERED",
        )
        .count()
    )
    failed_ev = (
        db.query(models.MasteryEvent)
        .filter(
            models.MasteryEvent.course_id == course_id,
            models.MasteryEvent.event_type == "REASSESSMENT_FAILED",
        )
        .count()
    )

    # Students requiring attention (aggregate warnings without N+1 explosion — batch)
    attention = faculty_attention(db, actor, course_id=course_id, limit=100)
    improving_students = {
        s.student_id
        for s in states
        if s.status in ("LEARNING", "READY_FOR_REASSESSMENT", "MASTERED")
        and s.practice_accuracy is not None
    }

    return {
        "course_id": course_id,
        "total_students": len(student_ids),
        "active_learning_gaps": len(active_gaps),
        "improving_students": len(improving_students),
        "students_requiring_attention": len({a["student_id"] for a in attention["items"]}),
        "mastery_distribution": dict(status_dist),
        "reassessment_outcomes": {
            "started": len(reass),
            "completed": sum(1 for a in reass if a.status == "COMPLETED"),
            "mastered_events": mastered_ev,
            "failed_events": failed_ev,
        },
        "remediation_outcomes": {
            "interventions_assigned": len(interventions),
            "interventions_completed": sum(1 for i in interventions if i.status == "COMPLETED"),
            "by_mode": dict(Counter(i.mode for i in interventions)),
        },
        "policy": mastery.get_policy(db, course_id),
        "warning_policy": ew.get_warning_policy(db, course_id),
    }


def faculty_topics(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    subject_id: Optional[int] = None,
) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    q = db.query(models.TopicMasteryState).filter(models.TopicMasteryState.course_id == course_id)
    if subject_id is not None:
        q = q.filter(models.TopicMasteryState.subject_id == subject_id)
    states = q.all()
    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.course_id == course_id,
            models.LearningGap.scope_type == "TOPIC",
        )
        .all()
    )
    by_topic: Dict[int, Dict[str, Any]] = {}
    topics = _topic_map(db, {s.topic_id for s in states} | {g.scope_id for g in gaps if g.scope_id})

    for s in states:
        bucket = by_topic.setdefault(
            s.topic_id,
            {
                "topic_id": s.topic_id,
                "topic_name": topics[s.topic_id].name if s.topic_id in topics else f"Topic {s.topic_id}",
                "subject_id": s.subject_id,
                "students_assessed": 0,
                "students_mastered": 0,
                "students_developing": 0,
                "students_needing_remediation": 0,
                "persistent_gap_count": 0,
                "status_counts": Counter(),
            },
        )
        bucket["students_assessed"] += 1
        bucket["status_counts"][s.status] += 1
        if s.status == "MASTERED":
            bucket["students_mastered"] += 1
        elif s.status in ("LEARNING", "NEEDS_PRACTICE", "READY_FOR_REASSESSMENT"):
            bucket["students_developing"] += 1
        elif s.status in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED"):
            bucket["students_needing_remediation"] += 1

    for g in gaps:
        if not g.scope_id or _gap_resolved(g):
            continue
        if g.classification not in ("WEAK", "CRITICAL_GAP", "DEVELOPING"):
            continue
        bucket = by_topic.setdefault(
            g.scope_id,
            {
                "topic_id": g.scope_id,
                "topic_name": g.scope_name or (topics[g.scope_id].name if g.scope_id in topics else f"Topic {g.scope_id}"),
                "subject_id": None,
                "students_assessed": 0,
                "students_mastered": 0,
                "students_developing": 0,
                "students_needing_remediation": 0,
                "persistent_gap_count": 0,
                "status_counts": Counter(),
            },
        )
        bucket["persistent_gap_count"] += 1

    rows = []
    for tid, b in by_topic.items():
        sc = dict(b["status_counts"])
        trend = "IMPROVING" if b["students_mastered"] > b["students_needing_remediation"] else "NEEDS_ATTENTION"
        if b["students_assessed"] == 0:
            trend = "INSUFFICIENT_DATA"
        rows.append(
            {
                **{k: v for k, v in b.items() if k != "status_counts"},
                "status_counts": sc,
                "improvement_trend": trend,
            }
        )
    rows.sort(key=lambda r: (-r["students_needing_remediation"], -r["persistent_gap_count"], r["topic_name"]))
    return {"course_id": course_id, "subject_id": subject_id, "topics": rows}


def faculty_attention(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    limit: int = 50,
) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    enrollments = (
        db.query(models.StudentCourseEnrollment.student_id)
        .filter(models.StudentCourseEnrollment.course_id == course_id)
        .all()
    )
    student_ids = [r[0] for r in enrollments]
    users = {
        u.id: u
        for u in db.query(models.User).filter(models.User.id.in_(student_ids or [-1])).all()
    }
    # Gap concentration for COMMON session recommendation
    gap_topic_counts: Counter = Counter()
    for g in (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.course_id == course_id,
            models.LearningGap.scope_type == "TOPIC",
        )
        .all()
    ):
        if _gap_resolved(g) or not g.scope_id:
            continue
        if g.classification in ("WEAK", "CRITICAL_GAP", "DEVELOPING"):
            gap_topic_counts[g.scope_id] += 1

    items = []
    warn_policy = ew.get_warning_policy(db, course_id)
    for sid in student_ids:
        signals = ew.evaluate_student_warnings(
            db, student_id=sid, course_id=course_id, policy=warn_policy
        )
        for sig in signals:
            if sig["code"] == "POSITIVE_PROGRESS":
                continue
            same = gap_topic_counts.get(sig.get("topic_id") or -1, 1)
            frec = ew.faculty_recommendation(
                code=sig["code"],
                status="",
                same_gap_student_count=same,
            )
            u = users.get(sid)
            items.append(
                {
                    "student_id": sid,
                    "student_name": u.name if u else None,
                    "topic_id": sig.get("topic_id"),
                    "topic_name": sig.get("topic_name"),
                    "current_state": sig.get("code"),
                    "severity": sig["severity"],
                    "evidence": sig.get("evidence"),
                    "reason": sig.get("reason"),
                    "recommended_action": frec,
                }
            )
    items.sort(key=lambda x: ({"URGENT_ATTENTION": 0, "ATTENTION_REQUIRED": 1, "WATCH": 2}.get(x["severity"], 9), x["student_id"]))
    return {"course_id": course_id, "items": items[:limit], "total": len(items)}


def faculty_interventions(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
) -> Dict[str, Any]:
    """Remediation effectiveness — observational associations, not causal claims."""
    _authorize_faculty_course(db, actor, course_id)
    interventions = (
        db.query(models.RemedialIntervention)
        .filter(models.RemedialIntervention.course_id == course_id)
        .all()
    )
    rows = []
    followed_mastery = 0
    followed_persist = 0
    for iv in interventions:
        snap = iv.gap_snapshot or {}
        topic_id = snap.get("scope_id") if snap.get("scope_type") == "TOPIC" else None
        student_ids: List[int] = []
        if iv.student_id:
            student_ids = [iv.student_id]
        elif iv.group_id:
            student_ids = [
                m.student_id
                for m in db.query(models.RemedialGroupMember)
                .filter(models.RemedialGroupMember.group_id == iv.group_id)
                .all()
            ]
        outcomes = []
        for sid in student_ids:
            state = None
            if topic_id:
                state = (
                    db.query(models.TopicMasteryState)
                    .filter(
                        models.TopicMasteryState.student_id == sid,
                        models.TopicMasteryState.course_id == course_id,
                        models.TopicMasteryState.topic_id == topic_id,
                    )
                    .first()
                )
            after_status = state.status if state else None
            after_pct = state.mastery_percent if state else None
            if after_status == "MASTERED":
                followed_mastery += 1
            elif after_status in ("NEEDS_REMEDIATION", "NEEDS_PRACTICE", "MASTERY_REGRESSED"):
                followed_persist += 1
            # before: gap snapshot evidence if present
            before_pct = None
            if isinstance(snap.get("evidence"), dict) and snap["evidence"].get("accuracy") is not None:
                before_pct = round(float(snap["evidence"]["accuracy"]) * 100, 2)
            outcomes.append(
                {
                    "student_id": sid,
                    "before_score_pct": before_pct,
                    "after_mastery_percent": after_pct,
                    "after_status": after_status,
                    "association": (
                        "followed_by_mastery"
                        if after_status == "MASTERED"
                        else "gap_may_persist"
                        if after_status in ("NEEDS_REMEDIATION", "NEEDS_PRACTICE")
                        else "insufficient_outcome_data"
                    ),
                }
            )
        rows.append(
            {
                "intervention_id": iv.id,
                "mode": iv.mode,
                "status": iv.status,
                "topic_id": topic_id,
                "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
                "outcomes": outcomes,
            }
        )
    return {
        "course_id": course_id,
        "interventions": rows,
        "summary": {
            "assigned": len(interventions),
            "completed": sum(1 for i in interventions if i.status == "COMPLETED"),
            "followed_by_mastery_count": followed_mastery,
            "associated_with_persistent_gap_count": followed_persist,
        },
        "caveat": "Associations only — do not interpret as proven causality.",
    }


def admin_overview(db: Session, actor: models.User, *, course_id: Optional[int] = None) -> Dict[str, Any]:
    _authorize_admin(actor)
    course_ids = [course_id] if course_id else [c[0] for c in db.query(models.Course.id).all()]
    if not course_ids:
        return {"courses": 0, "totals": {}}
    states = db.query(models.TopicMasteryState).filter(models.TopicMasteryState.course_id.in_(course_ids)).all()
    gaps = db.query(models.LearningGap).filter(models.LearningGap.course_id.in_(course_ids)).all()
    active_gaps = [g for g in gaps if not _gap_resolved(g) and g.classification in ("WEAK", "CRITICAL_GAP", "DEVELOPING")]
    interventions = (
        db.query(models.RemedialIntervention)
        .filter(models.RemedialIntervention.course_id.in_(course_ids))
        .all()
    )
    reass = (
        db.query(models.AdaptivePracticeAssignment)
        .filter(
            models.AdaptivePracticeAssignment.course_id.in_(course_ids),
            models.AdaptivePracticeAssignment.purpose == "REASSESSMENT",
        )
        .all()
    )
    attempts = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.course_id.in_(course_ids),
            models.AssessmentAttempt.status.in_(("SUBMITTED", "EVALUATED")),
        )
        .count()
    )
    return {
        "scope": {"course_id": course_id, "course_count": len(course_ids)},
        "totals": {
            "assessment_participation_attempts": attempts,
            "mastery_distribution": dict(Counter(s.status for s in states)),
            "active_learning_gaps": len(active_gaps),
            "remediation_demand_interventions": len(interventions),
            "intervention_completion": sum(1 for i in interventions if i.status == "COMPLETED"),
            "reassessment_started": len(reass),
            "reassessment_completed": sum(1 for a in reass if a.status == "COMPLETED"),
            "mastered_topic_states": sum(1 for s in states if s.status == "MASTERED"),
            "persistent_gap_proxy": sum(1 for s in states if s.status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED")),
        },
        "authority_note": "Institutional aggregates over authorized courses; no peer PII beyond aggregates.",
    }


def admin_courses(db: Session, actor: models.User) -> Dict[str, Any]:
    _authorize_admin(actor)
    courses = db.query(models.Course).all()
    rows = []
    for c in courses:
        ov = admin_overview(db, actor, course_id=c.id)
        rows.append({"course_id": c.id, "title": c.title, "totals": ov["totals"]})
    return {"courses": rows}


def admin_subjects(db: Session, actor: models.User, *, course_id: int) -> Dict[str, Any]:
    _authorize_admin(actor)
    subjects = db.query(models.Subject).filter(models.Subject.course_id == course_id).all()
    states = (
        db.query(models.TopicMasteryState)
        .filter(models.TopicMasteryState.course_id == course_id)
        .all()
    )
    by_subj: Dict[Optional[int], Counter] = defaultdict(Counter)
    for s in states:
        by_subj[s.subject_id][s.status] += 1
    rows = []
    for sub in subjects:
        rows.append(
            {
                "subject_id": sub.id,
                "name": sub.name,
                "mastery_distribution": dict(by_subj.get(sub.id, Counter())),
            }
        )
    return {"course_id": course_id, "subjects": rows}


def admin_attention(db: Session, actor: models.User, *, course_id: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    _authorize_admin(actor)
    course_ids = [course_id] if course_id else get_coordinated_course_ids(db, actor)
    items = []
    for cid in course_ids:
        # reuse faculty attention with admin actor (authorized)
        part = faculty_attention(db, actor, course_id=cid, limit=limit)
        for it in part["items"]:
            items.append({**it, "course_id": cid})
    items.sort(key=lambda x: ({"URGENT_ATTENTION": 0, "ATTENTION_REQUIRED": 1, "WATCH": 2}.get(x["severity"], 9)))
    return {"items": items[:limit], "total": len(items)}


def emit_attention_notifications(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    student_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Optional: emit Notification Engine events for high-severity attention signals."""
    _authorize_faculty_course(db, actor, course_id)
    emitted = 0
    if student_id:
        targets = [student_id]
    else:
        targets = [
            r[0]
            for r in db.query(models.StudentCourseEnrollment.student_id)
            .filter(models.StudentCourseEnrollment.course_id == course_id)
            .all()
        ]
    policy = ew.get_warning_policy(db, course_id)
    for sid in targets:
        for sig in ew.evaluate_student_warnings(db, student_id=sid, course_id=course_id, policy=policy):
            if sig["severity"] not in ("ATTENTION_REQUIRED", "URGENT_ATTENTION"):
                continue
            event = (
                "PERSISTENT_LEARNING_GAP_ALERT"
                if sig["code"] == "PERSISTENT_LEARNING_GAP"
                else "LEARNING_ATTENTION_SIGNAL"
            )
            if sig["code"] == "POSITIVE_PROGRESS":
                event = "IMPROVEMENT_MILESTONE"
            notif_svc.emit_event(
                db,
                event=event,
                title=sig["title"],
                message=sig["reason"],
                student_id=sid,
                course_id=course_id,
                severity="WARNING" if sig["severity"] != "URGENT_ATTENTION" else "CRITICAL",
                source_module="LEARNING_ANALYTICS",
                link_path="/analytics/me",
                payload=sig,
                channels=["IN_APP", "EMAIL"],
            )
            emitted += 1
    if not student_id:
        notif_svc.emit_event(
            db,
            event="FACULTY_ATTENTION_SUMMARY",
            title=f"Learning attention summary — course {course_id}",
            message=f"{emitted} attention signal(s) evaluated for enrolled students.",
            course_id=course_id,
            severity="INFO",
            source_module="LEARNING_ANALYTICS",
            link_path="/analytics",
            payload={"emitted": emitted, "course_id": course_id},
            channels=["IN_APP", "EMAIL"],
        )
    return {"emitted": emitted, "course_id": course_id}
