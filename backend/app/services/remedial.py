"""P0-014 Intelligent Remedial Learning — gap selection, explainable grouping, intervention plans.

Reuses P0-012 LearningGap rows and P0-013 learning sessions. Does not reimplement
performance analysis, notifications, or digital classroom teaching.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.academic_auth import (
    can_manage_learning_sessions,
    get_coordinated_course_ids,
    is_admin,
)
from app.constants import (
    REMEDIAL_GAP_ELIGIBLE_CLASSIFICATIONS,
    REMEDIAL_GROUP_STATUSES,
    REMEDIAL_GROUP_TRANSITIONS,
    REMEDIAL_INTERVENTION_STATUSES,
    REMEDIAL_INTERVENTION_TRANSITIONS,
    REMEDIAL_OUTCOMES,
)
from app.services import learning_sessions as ls
from app.services import notifications as notif_svc
from app.services import teaching_plans


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def severity_from_classification(classification: str) -> str:
    c = (classification or "").upper()
    if c == "CRITICAL_GAP":
        return "critical"
    if c == "WEAK":
        return "high"
    if c == "DEVELOPING":
        return "moderate"
    return "low"


def _gap_snapshot(gap: models.LearningGap) -> Dict[str, Any]:
    return {
        "learning_gap_id": gap.id,
        "student_id": gap.student_id,
        "course_id": gap.course_id,
        "scope_type": gap.scope_type,
        "scope_id": gap.scope_id,
        "scope_name": gap.scope_name,
        "classification": gap.classification,
        "severity": severity_from_classification(gap.classification),
        "confidence": gap.confidence,
        "priority_score": gap.priority_score,
        "is_high_priority": bool(gap.is_high_priority),
        "evidence": gap.evidence,
        "inference": gap.inference,
    }


def _require_course_manage(db: Session, user: models.User, course_id: int, subject_id: Optional[int] = None):
    if not can_manage_learning_sessions(db, user, course_id=course_id, subject_id=subject_id):
        raise _http(403, "Not authorized for remedial operations in this course")


def _can_view_course_remedial(db: Session, user: models.User, course_id: int) -> bool:
    if is_admin(user):
        return True
    if can_manage_learning_sessions(db, user, course_id=course_id):
        return True
    # enrolled student
    enr = (
        db.query(models.StudentCourseEnrollment)
        .filter(
            models.StudentCourseEnrollment.student_id == user.id,
            models.StudentCourseEnrollment.course_id == course_id,
        )
        .first()
    )
    return bool(enr)


def _subject_for_topic(db: Session, topic_id: Optional[int]) -> Optional[int]:
    if not topic_id:
        return None
    t = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    return t.subject_id if t else None


def list_eligible_gaps(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    student_id: Optional[int] = None,
    min_severity: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not _can_view_course_remedial(db, actor, course_id):
        raise _http(403, "Not authorized")
    role = (actor.role or "").lower()
    if role == "student":
        student_id = actor.id
    elif student_id is not None:
        if not notif_svc.user_can_view_student_performance(db, actor, student_id, course_id):
            raise _http(403, "Not authorized for this student's gaps")

    q = db.query(models.LearningGap).filter(
        models.LearningGap.course_id == course_id,
        models.LearningGap.classification.in_(REMEDIAL_GAP_ELIGIBLE_CLASSIFICATIONS),
    )
    if student_id is not None:
        q = q.filter(models.LearningGap.student_id == student_id)
    gaps = q.order_by(models.LearningGap.is_high_priority.desc(), models.LearningGap.id).all()

    sev_rank = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
    min_r = sev_rank.get((min_severity or "moderate").lower(), 1)
    out = []
    for g in gaps:
        snap = _gap_snapshot(g)
        if sev_rank.get(snap["severity"], 0) < min_r:
            continue
        if role == "student" and g.student_id != actor.id:
            continue
        out.append(snap)
    return out


def prioritize_student_gaps(gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sev_rank = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    ranked = sorted(
        gaps,
        key=lambda g: (
            sev_rank.get(g.get("severity") or "low", 9),
            0 if g.get("is_high_priority") else 1,
            -(float(g.get("priority_score") or 0)),
            g.get("learning_gap_id") or 0,
        ),
    )
    out = []
    for i, g in enumerate(ranked, start=1):
        reasons = []
        if g.get("severity") == "critical":
            reasons.append("Critical-severity classification from Performance Analyzer")
        elif g.get("severity") == "high":
            reasons.append("High-severity (WEAK) gap")
        else:
            reasons.append(f"Severity={g.get('severity')}")
        if g.get("is_high_priority"):
            reasons.append("Marked high-priority by analyzer (importance + weakness)")
        if g.get("priority_score"):
            reasons.append(f"Topic/concept importance score={g.get('priority_score')}")
        if i == 1 and g.get("severity") in ("critical", "high"):
            reasons.append("Foundational gaps are addressed before lower-severity topics")
        item = dict(g)
        item["priority_rank"] = i
        item["priority_explanation"] = "; ".join(reasons)
        out.append(item)
    return out


def _cluster_key(gap: models.LearningGap) -> Tuple[str, str, str]:
    scope_key = str(gap.scope_id) if gap.scope_id is not None else (gap.scope_name or "").strip().lower()
    return (gap.scope_type or "TOPIC", scope_key, severity_from_classification(gap.classification))


def propose_remedial_groups(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    persist: bool = True,
) -> Dict[str, Any]:
    _require_course_manage(db, actor, course_id)
    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.course_id == course_id,
            models.LearningGap.classification.in_(REMEDIAL_GAP_ELIGIBLE_CLASSIFICATIONS),
        )
        .all()
    )
    buckets: Dict[Tuple[str, str, str], List[models.LearningGap]] = defaultdict(list)
    for g in gaps:
        # Prefer topic/subject/concept scopes for grouping — skip DIFFICULTY-only
        if (g.scope_type or "").upper() == "DIFFICULTY":
            continue
        buckets[_cluster_key(g)].append(g)

    proposals = []
    individuals = []
    for key, rows in buckets.items():
        # Deduplicate by student (keep highest priority gap row)
        by_student: Dict[int, models.LearningGap] = {}
        for g in rows:
            prev = by_student.get(g.student_id)
            if not prev or (g.is_high_priority and not prev.is_high_priority):
                by_student[g.student_id] = g
            elif (g.priority_score or 0) > (prev.priority_score or 0):
                by_student[g.student_id] = g
        members = list(by_student.values())
        scope_type, scope_key, severity = key
        scope_name = members[0].scope_name or scope_key
        scope_id = members[0].scope_id
        subject_id = None
        topic_id = None
        if (scope_type or "").upper() == "TOPIC" and scope_id:
            topic_id = scope_id
            subject_id = _subject_for_topic(db, topic_id)
        elif (scope_type or "").upper() == "SUBJECT" and scope_id:
            subject_id = scope_id

        if len(members) >= 2:
            student_ids = sorted(m.student_id for m in members)
            explanation = {
                "summary": (
                    f"Students share a {severity}-severity learning gap in "
                    f'"{scope_name}" ({scope_type}).'
                ),
                "why_students_selected": [
                    f"Student {m.student_id}: gap classification={m.classification}, "
                    f"high_priority={bool(m.is_high_priority)}"
                    for m in members
                ],
                "why_topic_selected": f"P0-012 Learning Gap Detection identified {scope_type} '{scope_name}'",
                "why_grouped": [
                    "Same course academic scope",
                    f"Same scope_type={scope_type} and scope identity",
                    f"Compatible severity band={severity}",
                    "Grouping uses learning-gap similarity, not raw overall scores",
                ],
                "common_evidence": [
                    {
                        "student_id": m.student_id,
                        "classification": m.classification,
                        "accuracy": (m.evidence or {}).get("accuracy") if isinstance(m.evidence, dict) else None,
                        "repeated_error_questions": (m.evidence or {}).get("repeated_error_questions")
                        if isinstance(m.evidence, dict)
                        else None,
                    }
                    for m in members
                ],
            }
            similarity = {
                "algorithm": "deterministic_rule_based_v1",
                "signals": {
                    "topic_overlap": 1.0,
                    "scope_type_match": 1.0,
                    "severity_compatibility": 1.0,
                    "course_compatibility": 1.0,
                },
                "score": 1.0,
                "member_count": len(members),
                "student_ids": student_ids,
            }
            item = {
                "kind": "COMMON",
                "course_id": course_id,
                "subject_id": subject_id,
                "topic_id": topic_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "scope_name": scope_name,
                "severity": severity,
                "explanation": explanation,
                "similarity": similarity,
                "members": [_gap_snapshot(m) for m in members],
            }
            if persist:
                group = models.RemedialGroup(
                    course_id=course_id,
                    subject_id=subject_id,
                    topic_id=topic_id,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    scope_name=scope_name,
                    severity=severity,
                    status="PROPOSED",
                    explanation=explanation,
                    similarity=similarity,
                    created_by=actor.id,
                )
                db.add(group)
                db.flush()
                for m in members:
                    db.add(
                        models.RemedialGroupMember(
                            group_id=group.id,
                            student_id=m.student_id,
                            learning_gap_id=m.id,
                            gap_snapshot=_gap_snapshot(m),
                            status="INVITED",
                        )
                    )
                item["id"] = group.id
                item["status"] = group.status
            proposals.append(item)
        else:
            g = members[0]
            ranked = prioritize_student_gaps([_gap_snapshot(g)])[0]
            individuals.append(
                {
                    "kind": "INDIVIDUAL",
                    "student_id": g.student_id,
                    "gap": ranked,
                    "explanation": {
                        "summary": (
                            f"Student {g.student_id} has a unique or non-shared "
                            f"{ranked['severity']}-severity gap in \"{g.scope_name}\"."
                        ),
                        "why_individual": "Fewer than two students share this gap signature in-course",
                        "why_topic_selected": f"Analyzer gap on {g.scope_type} '{g.scope_name}'",
                    },
                }
            )

    if persist:
        db.commit()

    return {
        "course_id": course_id,
        "common_groups": proposals,
        "individual_candidates": individuals,
        "algorithm": "deterministic_rule_based_v1",
        "note": "Grouping uses learning-gap similarity within academic course boundaries.",
    }


def _build_intervention_plan(
    *,
    mode: str,
    gap: Dict[str, Any],
    intervention_type: str,
) -> Dict[str, Any]:
    topic = gap.get("scope_name") or "Target topic"
    return {
        "target_topic": topic,
        "target_scope_type": gap.get("scope_type"),
        "target_scope_id": gap.get("scope_id"),
        "learning_gap": {
            "classification": gap.get("classification"),
            "severity": gap.get("severity"),
            "confidence": gap.get("confidence"),
        },
        "learning_objective": f"Strengthen understanding of {topic} to resolve the identified learning gap.",
        "intervention_type": intervention_type,
        "recommended_sequence": [
            "AI Lecturer introduction of the gap concept",
            "Visual / board explanation (2D or 3D when spatial value exists)",
            "Worked example",
            "Guided practice check",
            "Summary and reassessment recommendation",
        ],
        "estimated_learning_scope": "Focused remedial session (single topic/concept)",
        "prerequisite_concepts": [],
        "success_criteria": [
            "Student completes the remedial learning session",
            "Understanding check answered or reviewed",
            "Reassessment scheduled when required",
        ],
        "reassessment_requirement": True,
        "ai_lecturer_context": {
            "intervention_goal": f"Remediate {gap.get('severity')} gap in {topic}",
            "gap_classification": gap.get("classification"),
            "difficulty_context": "remedial",
            "visual_preference": teaching_plans.select_visual_type(
                concept=topic, domain_hint=str(gap.get("scope_type") or "")
            ),
        },
        "session_mode": mode,
    }


def create_individual_intervention(
    db: Session,
    actor: models.User,
    *,
    course_id: int,
    learning_gap_id: int,
) -> models.RemedialIntervention:
    _require_course_manage(db, actor, course_id)
    gap = (
        db.query(models.LearningGap)
        .filter(models.LearningGap.id == learning_gap_id, models.LearningGap.course_id == course_id)
        .first()
    )
    if not gap:
        raise _http(404, "Learning gap not found")
    if gap.classification not in REMEDIAL_GAP_ELIGIBLE_CLASSIFICATIONS:
        raise _http(422, "Gap classification is not eligible for remediation")
    snap = _gap_snapshot(gap)
    ranked = prioritize_student_gaps([snap])[0]
    itype = "INDIVIDUAL_EXPLANATION"
    if snap["severity"] in ("critical", "high"):
        itype = "AI_LECTURER_EXPLANATION"
    plan = _build_intervention_plan(mode="INDIVIDUAL", gap=snap, intervention_type=itype)
    explanation = {
        "why_student_selected": f"Student {gap.student_id} has eligible gap '{gap.scope_name}'",
        "why_topic_selected": f"{gap.scope_type} gap from P0-012 analyzer",
        "why_intervention_selected": f"{itype} matches individual unique/non-shared gap",
        "priority": ranked.get("priority_explanation"),
    }
    row = models.RemedialIntervention(
        course_id=course_id,
        student_id=gap.student_id,
        group_id=None,
        learning_gap_id=gap.id,
        gap_snapshot=snap,
        intervention_type=itype,
        mode="INDIVIDUAL",
        priority_rank=ranked["priority_rank"],
        priority_explanation=ranked["priority_explanation"],
        plan=plan,
        explanation=explanation,
        status="DRAFT",
        outcome="PENDING",
        reassessment_required=True,
        created_by=actor.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_group_intervention(
    db: Session,
    actor: models.User,
    *,
    group_id: int,
) -> models.RemedialIntervention:
    group = db.query(models.RemedialGroup).filter(models.RemedialGroup.id == group_id).first()
    if not group:
        raise _http(404, "Remedial group not found")
    _require_course_manage(db, actor, group.course_id, group.subject_id)
    if group.status not in ("PROPOSED", "APPROVED", "ACTIVATED", "IN_PROGRESS"):
        raise _http(422, f"Cannot plan intervention for group status {group.status}")
    existing = (
        db.query(models.RemedialIntervention)
        .filter(
            models.RemedialIntervention.group_id == group_id,
            models.RemedialIntervention.status.notin_(("CANCELLED",)),
        )
        .first()
    )
    if existing:
        return existing

    members = [m for m in (group.members or []) if m.status != "REMOVED"]
    if not members:
        raise _http(422, "Group has no members")
    snap = dict(members[0].gap_snapshot or {})
    snap["scope_name"] = group.scope_name
    snap["scope_type"] = group.scope_type
    snap["scope_id"] = group.scope_id
    snap["severity"] = group.severity
    itype = "GROUP_REMEDIAL_LECTURE"
    plan = _build_intervention_plan(mode="COMMON", gap=snap, intervention_type=itype)
    explanation = {
        "why_students_selected": [f"Member student_id={m.student_id}" for m in members],
        "why_topic_selected": group.explanation.get("why_topic_selected") if group.explanation else group.scope_name,
        "why_intervention_selected": "Shared gap → COMMON AI Lecturer remedial lecture",
        "why_grouped": (group.explanation or {}).get("why_grouped"),
        "group_summary": (group.explanation or {}).get("summary"),
    }
    row = models.RemedialIntervention(
        course_id=group.course_id,
        student_id=None,
        group_id=group.id,
        learning_gap_id=members[0].learning_gap_id,
        gap_snapshot=snap,
        intervention_type=itype,
        mode="COMMON",
        priority_rank=1,
        priority_explanation=f"Shared {group.severity} gap in {group.scope_name}",
        plan=plan,
        explanation=explanation,
        status="DRAFT",
        outcome="PENDING",
        reassessment_required=True,
        created_by=actor.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _attach_remedial_lecture(
    db: Session,
    actor: models.User,
    session: models.LearningSession,
    intervention: models.RemedialIntervention,
) -> None:
    """Seed a LECTURE activity with remedial AI Lecturer context (P0-013.4)."""
    plan_ctx = (intervention.plan or {}).get("ai_lecturer_context") or {}
    topic = (intervention.gap_snapshot or {}).get("scope_name") or session.title
    teaching_plan = teaching_plans.build_teaching_plan(
        title=session.title,
        topic_title=topic,
        subject_name="",
        objectives=[(intervention.plan or {}).get("learning_objective") or f"Remediate {topic}"],
    )
    teaching_plan["remedial"] = {
        "intervention_id": intervention.id,
        "gap": intervention.gap_snapshot,
        "ai_lecturer_context": plan_ctx,
    }
    ls.add_activity(
        db,
        actor,
        session.id,
        activity_type="LECTURE",
        title=f"Remedial lecture — {topic}",
        description="P0-014 remedial intervention via AI Lecturer digital classroom",
        sequence=1,
        scope="COMMON",
        payload={
            "teaching_plan": teaching_plan,
            "lecture_meta": {"provider": "ai_lecturer", "version": 1, "remedial": True},
            "remedial_intervention_id": intervention.id,
        },
    )
    ls.add_objective(
        db,
        actor,
        session.id,
        statement=(intervention.plan or {}).get("learning_objective") or f"Close gap in {topic}",
        sequence=1,
        subject_id=session.subject_id,
        topic_id=session.topic_id,
        concept_tag=(intervention.gap_snapshot or {}).get("scope_name"),
    )


def activate_group(
    db: Session,
    actor: models.User,
    group_id: int,
) -> Dict[str, Any]:
    group = db.query(models.RemedialGroup).filter(models.RemedialGroup.id == group_id).first()
    if not group:
        raise _http(404, "Remedial group not found")
    _require_course_manage(db, actor, group.course_id, group.subject_id)
    if group.status not in ("PROPOSED", "APPROVED"):
        raise _http(422, f"Cannot activate from status {group.status}")

    intervention = create_group_intervention(db, actor, group_id=group.id)
    session = ls.create_session(
        db,
        actor,
        title=f"Remedial: {group.scope_name}",
        description=(group.explanation or {}).get("summary"),
        mode="COMMON",
        course_id=group.course_id,
        subject_id=group.subject_id,
        topic_id=group.topic_id,
    )
    for m in group.members:
        if m.status == "REMOVED":
            continue
        ls.add_participant(db, actor, session.id, user_id=m.student_id, role="STUDENT")
        m.status = "ACTIVE"

    _attach_remedial_lecture(db, actor, session, intervention)

    group.status = "ACTIVATED"
    group.learning_session_id = session.id
    group.activated_at = _utcnow()
    intervention.status = "ASSIGNED"
    intervention.learning_session_id = session.id
    db.commit()
    db.refresh(group)
    db.refresh(intervention)

    for m in group.members:
        if m.status == "REMOVED":
            continue
        notif_svc.emit_event(
            db,
            event="REMEDIAL_GROUP_ASSIGNED",
            title=f"Remedial group: {group.scope_name}",
            message=(
                f"You were added to a remedial learning group for \"{group.scope_name}\" "
                f"because of a shared learning gap. Open your classroom session when ready."
            ),
            student_id=m.student_id,
            course_id=group.course_id,
            severity="WARNING" if group.severity in ("high", "critical") else "INFO",
            source_module="REMEDIAL",
            link_path=f"/learning-sessions/{session.id}/lecture",
            payload={
                "group_id": group.id,
                "intervention_id": intervention.id,
                "session_id": session.id,
                "explanation": group.explanation,
            },
            channels=["IN_APP", "EMAIL"],
        )
        notif_svc.emit_event(
            db,
            event="REMEDIAL_SESSION_AVAILABLE",
            title="Remedial AI Lecturer session available",
            message=f"A remedial digital classroom session is ready for {group.scope_name}.",
            student_id=m.student_id,
            course_id=group.course_id,
            source_module="REMEDIAL",
            link_path=f"/learning-sessions/{session.id}/lecture",
            payload={"session_id": session.id, "intervention_id": intervention.id},
            channels=["IN_APP", "EMAIL"],
        )

    return group_to_dict(db, group, include_members=True, intervention=intervention)


def activate_individual_intervention(
    db: Session,
    actor: models.User,
    intervention_id: int,
) -> models.RemedialIntervention:
    row = db.query(models.RemedialIntervention).filter(models.RemedialIntervention.id == intervention_id).first()
    if not row:
        raise _http(404, "Intervention not found")
    if row.group_id:
        raise _http(422, "Use group activation for group interventions")
    _require_course_manage(db, actor, row.course_id)
    if row.status not in ("DRAFT", "ASSIGNED"):
        raise _http(422, f"Cannot activate from status {row.status}")
    if not row.student_id:
        raise _http(422, "Individual intervention requires student_id")

    gap = row.gap_snapshot or {}
    topic_id = gap.get("scope_id") if (gap.get("scope_type") or "").upper() == "TOPIC" else None
    subject_id = gap.get("scope_id") if (gap.get("scope_type") or "").upper() == "SUBJECT" else None
    if topic_id and not subject_id:
        subject_id = _subject_for_topic(db, topic_id)

    session = ls.create_session(
        db,
        actor,
        title=f"Remedial (Individual): {gap.get('scope_name') or 'Learning gap'}",
        description=(row.explanation or {}).get("why_intervention_selected"),
        mode="INDIVIDUAL",
        course_id=row.course_id,
        subject_id=subject_id,
        topic_id=topic_id,
        primary_student_id=row.student_id,
    )
    _attach_remedial_lecture(db, actor, session, row)
    row.learning_session_id = session.id
    row.status = "ASSIGNED"
    db.commit()
    db.refresh(row)

    notif_svc.emit_event(
        db,
        event="REMEDIAL_INTERVENTION_ASSIGNED",
        title="Remedial learning assigned",
        message=(
            f"A personal remedial session was assigned for \"{gap.get('scope_name')}\". "
            f"Reason: {(row.explanation or {}).get('why_topic_selected', 'learning gap detected')}."
        ),
        student_id=row.student_id,
        course_id=row.course_id,
        source_module="REMEDIAL",
        link_path=f"/learning-sessions/{session.id}/lecture",
        payload={"intervention_id": row.id, "session_id": session.id, "explanation": row.explanation},
        channels=["IN_APP", "EMAIL"],
    )
    notif_svc.emit_event(
        db,
        event="REMEDIAL_PLAN_AVAILABLE",
        title="Your remedial plan is ready",
        message="Review your intervention plan and enter the AI Lecturer classroom.",
        student_id=row.student_id,
        course_id=row.course_id,
        source_module="REMEDIAL",
        link_path="/remedial/me",
        payload={"intervention_id": row.id},
        channels=["IN_APP", "EMAIL"],
    )
    return row


def transition_group_status(
    db: Session, actor: models.User, group_id: int, new_status: str
) -> models.RemedialGroup:
    group = db.query(models.RemedialGroup).filter(models.RemedialGroup.id == group_id).first()
    if not group:
        raise _http(404, "Remedial group not found")
    _require_course_manage(db, actor, group.course_id, group.subject_id)
    new_status = (new_status or "").upper()
    if new_status not in REMEDIAL_GROUP_STATUSES:
        raise _http(422, f"Invalid status: {new_status}")
    allowed = REMEDIAL_GROUP_TRANSITIONS.get(group.status, set())
    if new_status not in allowed:
        raise _http(422, f"Cannot transition {group.status} → {new_status}")
    group.status = new_status
    if new_status == "COMPLETED":
        group.completed_at = _utcnow()
    db.commit()
    db.refresh(group)
    return group


def update_intervention_status(
    db: Session,
    actor: models.User,
    intervention_id: int,
    *,
    status_value: Optional[str] = None,
    outcome: Optional[str] = None,
    reassessment_required: Optional[bool] = None,
    reassessment_completed: Optional[bool] = None,
) -> models.RemedialIntervention:
    row = db.query(models.RemedialIntervention).filter(models.RemedialIntervention.id == intervention_id).first()
    if not row:
        raise _http(404, "Intervention not found")
    role = (actor.role or "").lower()
    if role == "student":
        if row.student_id != actor.id and not _student_in_group(db, row.group_id, actor.id):
            raise _http(403, "Not your intervention")
        # Students may only mark progress-related flags via complete path below
        if status_value and status_value.upper() not in ("IN_PROGRESS", "COMPLETED"):
            raise _http(403, "Students cannot set this intervention status")
    else:
        _require_course_manage(db, actor, row.course_id)

    if status_value is not None:
        status_value = status_value.upper()
        if status_value not in REMEDIAL_INTERVENTION_STATUSES:
            raise _http(422, f"Invalid intervention status: {status_value}")
        allowed = REMEDIAL_INTERVENTION_TRANSITIONS.get(row.status, set())
        if status_value not in allowed and status_value != row.status:
            raise _http(422, f"Cannot transition {row.status} → {status_value}")
        row.status = status_value
        if status_value == "COMPLETED":
            row.completed_at = _utcnow()
            if row.group_id:
                g = db.query(models.RemedialGroup).filter(models.RemedialGroup.id == row.group_id).first()
                if g and g.status in ("ACTIVATED", "IN_PROGRESS"):
                    g.status = "COMPLETED"
                    g.completed_at = _utcnow()

    if outcome is not None:
        outcome = outcome.upper()
        if outcome not in REMEDIAL_OUTCOMES:
            raise _http(422, f"Invalid outcome: {outcome}")
        row.outcome = outcome
    if reassessment_required is not None:
        row.reassessment_required = bool(reassessment_required)
    if reassessment_completed is not None:
        row.reassessment_completed = bool(reassessment_completed)
        if row.reassessment_completed and row.outcome == "PENDING":
            row.outcome = "IMPROVING"

    db.commit()
    db.refresh(row)

    if row.status == "COMPLETED":
        recipients = []
        if row.student_id:
            recipients = [row.student_id]
        elif row.group_id:
            recipients = [
                m.student_id
                for m in db.query(models.RemedialGroupMember)
                .filter(
                    models.RemedialGroupMember.group_id == row.group_id,
                    models.RemedialGroupMember.status != "REMOVED",
                )
                .all()
            ]
        for sid in recipients:
            notif_svc.emit_event(
                db,
                event="REMEDIAL_INTERVENTION_COMPLETED",
                title="Remedial intervention completed",
                message="Your remedial learning intervention was marked completed.",
                student_id=sid,
                course_id=row.course_id,
                source_module="REMEDIAL",
                link_path="/remedial/me",
                payload={"intervention_id": row.id, "outcome": row.outcome},
                channels=["IN_APP", "EMAIL"],
            )
            if row.reassessment_required and not row.reassessment_completed:
                notif_svc.emit_event(
                    db,
                    event="REMEDIAL_REASSESSMENT_REQUIRED",
                    title="Reassessment required",
                    message="Complete a reassessment to confirm the learning gap is improving.",
                    student_id=sid,
                    course_id=row.course_id,
                    severity="WARNING",
                    source_module="REMEDIAL",
                    link_path="/remedial/me",
                    payload={"intervention_id": row.id},
                    channels=["IN_APP", "EMAIL"],
                )
    return row


def _student_in_group(db: Session, group_id: Optional[int], student_id: int) -> bool:
    if not group_id:
        return False
    m = (
        db.query(models.RemedialGroupMember)
        .filter(
            models.RemedialGroupMember.group_id == group_id,
            models.RemedialGroupMember.student_id == student_id,
            models.RemedialGroupMember.status != "REMOVED",
        )
        .first()
    )
    return bool(m)


def get_group(db: Session, actor: models.User, group_id: int) -> Dict[str, Any]:
    group = db.query(models.RemedialGroup).filter(models.RemedialGroup.id == group_id).first()
    if not group:
        raise _http(404, "Remedial group not found")
    role = (actor.role or "").lower()
    if role == "student":
        if not _student_in_group(db, group.id, actor.id):
            raise _http(403, "Not a member of this remedial group")
        return group_to_dict(db, group, include_members=False, student_view=True, viewer_id=actor.id)
    _require_course_manage(db, actor, group.course_id, group.subject_id)
    return group_to_dict(db, group, include_members=True)


def list_groups(
    db: Session,
    actor: models.User,
    *,
    course_id: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    role = (actor.role or "").lower()
    q = db.query(models.RemedialGroup)
    if role == "student":
        q = (
            q.join(models.RemedialGroupMember)
            .filter(
                models.RemedialGroupMember.student_id == actor.id,
                models.RemedialGroupMember.status != "REMOVED",
            )
        )
        if course_id is not None:
            q = q.filter(models.RemedialGroup.course_id == course_id)
    else:
        if course_id is not None:
            _require_course_manage(db, actor, course_id)
            q = q.filter(models.RemedialGroup.course_id == course_id)
        elif not is_admin(actor):
            ids = get_coordinated_course_ids(db, actor)
            if not ids:
                return []
            q = q.filter(models.RemedialGroup.course_id.in_(ids))
    if status_filter:
        q = q.filter(models.RemedialGroup.status == status_filter.upper())
    rows = q.order_by(models.RemedialGroup.id.desc()).limit(200).all()
    if role == "student":
        return [group_to_dict(db, g, include_members=False, student_view=True, viewer_id=actor.id) for g in rows]
    return [group_to_dict(db, g, include_members=True) for g in rows]


def list_interventions_for_user(
    db: Session,
    actor: models.User,
    *,
    course_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    role = (actor.role or "").lower()
    if role == "student":
        q = db.query(models.RemedialIntervention).filter(
            models.RemedialIntervention.status != "CANCELLED"
        )
        # individual
        own = q.filter(models.RemedialIntervention.student_id == actor.id)
        if course_id is not None:
            own = own.filter(models.RemedialIntervention.course_id == course_id)
        rows = list(own.all())
        # group memberships
        gids = [
            m.group_id
            for m in db.query(models.RemedialGroupMember)
            .filter(
                models.RemedialGroupMember.student_id == actor.id,
                models.RemedialGroupMember.status != "REMOVED",
            )
            .all()
        ]
        if gids:
            gq = db.query(models.RemedialIntervention).filter(
                models.RemedialIntervention.group_id.in_(gids),
                models.RemedialIntervention.status != "CANCELLED",
            )
            if course_id is not None:
                gq = gq.filter(models.RemedialIntervention.course_id == course_id)
            rows.extend(gq.all())
        # dedupe
        seen = set()
        uniq = []
        for r in rows:
            if r.id in seen:
                continue
            seen.add(r.id)
            uniq.append(r)
        return [intervention_to_dict(r, student_view=True) for r in uniq]

    q = db.query(models.RemedialIntervention)
    if course_id is not None:
        _require_course_manage(db, actor, course_id)
        q = q.filter(models.RemedialIntervention.course_id == course_id)
    elif not is_admin(actor):
        ids = get_coordinated_course_ids(db, actor)
        if not ids:
            return []
        q = q.filter(models.RemedialIntervention.course_id.in_(ids))
    rows = q.order_by(models.RemedialIntervention.priority_rank, models.RemedialIntervention.id.desc()).limit(300).all()
    return [intervention_to_dict(r) for r in rows]


def get_intervention(db: Session, actor: models.User, intervention_id: int) -> Dict[str, Any]:
    row = db.query(models.RemedialIntervention).filter(models.RemedialIntervention.id == intervention_id).first()
    if not row:
        raise _http(404, "Intervention not found")
    role = (actor.role or "").lower()
    if role == "student":
        if row.student_id == actor.id or _student_in_group(db, row.group_id, actor.id):
            return intervention_to_dict(row, student_view=True)
        raise _http(403, "Not authorized")
    _require_course_manage(db, actor, row.course_id)
    return intervention_to_dict(row)


def group_to_dict(
    db: Session,
    group: models.RemedialGroup,
    *,
    include_members: bool = True,
    student_view: bool = False,
    viewer_id: Optional[int] = None,
    intervention: Optional[models.RemedialIntervention] = None,
) -> Dict[str, Any]:
    if intervention is None:
        intervention = (
            db.query(models.RemedialIntervention)
            .filter(
                models.RemedialIntervention.group_id == group.id,
                models.RemedialIntervention.status != "CANCELLED",
            )
            .order_by(models.RemedialIntervention.id.desc())
            .first()
        )
    data = {
        "id": group.id,
        "course_id": group.course_id,
        "subject_id": group.subject_id,
        "topic_id": group.topic_id,
        "scope_type": group.scope_type,
        "scope_id": group.scope_id,
        "scope_name": group.scope_name,
        "severity": group.severity,
        "status": group.status,
        "explanation": group.explanation,
        "similarity": group.similarity if not student_view else {
            "summary": (group.explanation or {}).get("summary"),
            "why_grouped": (group.explanation or {}).get("why_grouped"),
        },
        "learning_session_id": group.learning_session_id,
        "created_by": group.created_by,
        "created_at": group.created_at,
        "activated_at": group.activated_at,
        "completed_at": group.completed_at,
        "intervention": intervention_to_dict(intervention, student_view=student_view) if intervention else None,
    }
    if include_members and not student_view:
        data["members"] = [
            {
                "id": m.id,
                "student_id": m.student_id,
                "learning_gap_id": m.learning_gap_id,
                "gap_snapshot": m.gap_snapshot,
                "status": m.status,
            }
            for m in (group.members or [])
            if m.status != "REMOVED"
        ]
        data["member_count"] = len(data["members"])
    elif student_view:
        data["member_count"] = sum(1 for m in (group.members or []) if m.status != "REMOVED")
        data["student_friendly_reason"] = (group.explanation or {}).get("summary")
        # Never expose other students' performance details
        data.pop("similarity_detail", None)
    return data


def intervention_to_dict(
    row: Optional[models.RemedialIntervention],
    *,
    student_view: bool = False,
) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    gap = row.gap_snapshot or {}
    data = {
        "id": row.id,
        "course_id": row.course_id,
        "student_id": row.student_id if not student_view or row.student_id else None,
        "group_id": row.group_id,
        "learning_gap_id": row.learning_gap_id,
        "gap_snapshot": {
            "scope_type": gap.get("scope_type"),
            "scope_id": gap.get("scope_id"),
            "scope_name": gap.get("scope_name"),
            "classification": gap.get("classification"),
            "severity": gap.get("severity"),
            "is_high_priority": gap.get("is_high_priority"),
        }
        if student_view
        else gap,
        "intervention_type": row.intervention_type,
        "mode": row.mode,
        "priority_rank": row.priority_rank,
        "priority_explanation": row.priority_explanation,
        "plan": row.plan,
        "explanation": {
            "why_assigned": (row.explanation or {}).get("why_topic_selected")
            or (row.explanation or {}).get("why_student_selected"),
            "why_intervention": (row.explanation or {}).get("why_intervention_selected"),
            "group_summary": (row.explanation or {}).get("group_summary"),
        }
        if student_view
        else row.explanation,
        "status": row.status,
        "outcome": row.outcome,
        "reassessment_required": row.reassessment_required,
        "reassessment_completed": row.reassessment_completed,
        "learning_session_id": row.learning_session_id,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }
    return data
