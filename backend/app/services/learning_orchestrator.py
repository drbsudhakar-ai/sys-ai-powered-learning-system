"""P0-017 Personalized Learning Journey & Learning Orchestration.

Coordinates existing SYS engines. Does not recalculate mastery, gaps,
remediation grouping, adaptive practice, assessments, or early-warning scores.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.academic_auth import can_access_course_questions, is_admin
from app.constants import (
    LEARNING_ACTION_OPEN_STATUSES,
    LEARNING_ACTION_TYPES,
    LEARNING_HIERARCHY_RANKS,
)
from app.services import early_warning as ew
from app.services import mastery_engine as mastery
from app.services import notifications as notif_svc


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _authorize_student_view(db: Session, actor: models.User, student_id: int, course_id: int) -> None:
    if not notif_svc.user_can_view_student_performance(db, actor, student_id, course_id):
        raise _http(403, "Not authorized for this student learning journey")


def _authorize_faculty_course(db: Session, actor: models.User, course_id: int) -> None:
    role = (actor.role or "").lower()
    if role == "student":
        raise _http(403, "Faculty or admin access required")
    if is_admin(actor):
        return
    if can_access_course_questions(db, actor, course_id):
        return
    raise _http(403, "Not authorized for this course learning journey")


def _authorize_admin(actor: models.User) -> None:
    if not is_admin(actor):
        raise _http(403, "Admin access required")


def _require_enrollment(db: Session, student_id: int, course_id: int) -> None:
    enr = (
        db.query(models.StudentCourseEnrollment)
        .filter(
            models.StudentCourseEnrollment.student_id == student_id,
            models.StudentCourseEnrollment.course_id == course_id,
        )
        .first()
    )
    if not enr:
        raise _http(403, "Not enrolled in this course")


def _gap_resolved(gap: models.LearningGap) -> bool:
    return str((gap.inference or {}).get("mastery_status") or "").upper() == "RESOLVED"


def _topic_name(topic: Optional[models.Topic], topic_id: Optional[int]) -> str:
    if topic:
        return topic.name
    if topic_id:
        return f"Topic {topic_id}"
    return "this topic"


def _stable_key(
    *,
    action_type: str,
    topic_id: Optional[int],
    ref_kind: str = "",
    ref_id: Any = "",
) -> str:
    return f"{action_type}:{topic_id or 0}:{ref_kind}:{ref_id or 0}"


def _priority_rank(priority: str) -> int:
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "OPTIONAL": 4}
    return order.get(priority, 9)


def _sort_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda x: (
            int(x.get("hierarchy_rank") or 99),
            _priority_rank(x.get("priority") or "MEDIUM"),
            x.get("target_topic_id") or 0,
            x.get("action_type") or "",
        ),
    )


def _explain(
    *,
    what: str,
    why: str,
    source: str,
    outcome: str,
    action_type: str,
) -> Dict[str, str]:
    """Deterministic, student-facing explanation (not an academic decision)."""
    return {
        "what": what,
        "why": why,
        "source": source,
        "outcome": outcome,
        "summary": f"{what} {why} After you finish, {outcome[0].lower() + outcome[1:] if outcome else 'your learning status will update.'}",
        "action_type": action_type,
    }


def _href_for(action_type: str, ref: Optional[Dict[str, Any]]) -> Optional[str]:
    ref = ref or {}
    if ref.get("session_id"):
        return f"/learning-sessions/{ref['session_id']}/lecture"
    if ref.get("assessment_id"):
        return f"/student/assessments/{ref['assessment_id']}/start"
    if ref.get("attempt_id"):
        return f"/student/attempts/{ref['attempt_id']}"
    if action_type == "COMPLETE_REMEDIATION":
        return "/remedial/me"
    if action_type in ("ADAPTIVE_PRACTICE", "PRACTICE", "TAKE_REASSESSMENT", "RETRY"):
        return "/mastery/me"
    if action_type in ("START_AI_LECTURE", "WATCH_LECTURE", "CONTINUE_LEARNING", "ASK_LECTURER"):
        return "/learning-sessions"
    if action_type == "TAKE_ASSESSMENT":
        return "/student/assessments"
    if action_type == "HUMAN_EXPERT_SUPPORT":
        return "/remedial/me"
    if action_type == "REVIEW_MISTAKES":
        return "/my-performance"
    return "/learning-journey/me"


# ---------------------------------------------------------------------------
# Candidate generation (pure over gathered snapshots)
# ---------------------------------------------------------------------------

def build_candidates(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic action candidates from authoritative snapshots.

    snapshot keys: course_id, topics, states, gaps, interventions, sessions,
    lecture_resume, attempts, assignments, warnings, published_assessments, next_topic
    """
    course_id = snapshot["course_id"]
    states: Dict[int, models.TopicMasteryState] = snapshot["states"]
    topics: Dict[int, models.Topic] = snapshot["topics"]
    candidates: List[Dict[str, Any]] = []

    def add(**kwargs: Any) -> None:
        topic_id = kwargs.get("target_topic_id")
        topic = topics.get(topic_id) if topic_id else None
        ref = kwargs.get("resource_reference") or {}
        action_type = kwargs["action_type"]
        expl = kwargs.get("explanation") or _explain(
            what=kwargs["title"],
            why=kwargs["reason"],
            source=kwargs["source"],
            outcome=kwargs.get("outcome") or "Existing learning engines will update your status.",
            action_type=action_type,
        )
        candidates.append(
            {
                "action_type": action_type,
                "title": kwargs["title"],
                "description": kwargs.get("description") or kwargs["reason"],
                "reason": kwargs["reason"],
                "priority": kwargs.get("priority") or "MEDIUM",
                "source": kwargs["source"],
                "hierarchy_group": kwargs["hierarchy_group"],
                "hierarchy_rank": LEARNING_HIERARCHY_RANKS[kwargs["hierarchy_group"]],
                "target_course_id": course_id,
                "target_subject_id": kwargs.get("target_subject_id") or (topic.subject_id if topic else None),
                "target_topic_id": topic_id,
                "target_unit_id": None,
                "resource_reference": ref,
                "prerequisites": kwargs.get("prerequisites") or [],
                "mandatory": bool(kwargs.get("mandatory")),
                "explanation": expl,
                "href": _href_for(action_type, ref),
                "stable_key": _stable_key(
                    action_type=action_type,
                    topic_id=topic_id,
                    ref_kind=ref.get("kind") or "",
                    ref_id=ref.get("id") or ref.get("session_id") or ref.get("assessment_id") or ref.get("intervention_id") or "",
                ),
            }
        )

    # 1. Unfinished required activity
    for att in snapshot.get("open_attempts") or []:
        a = att.assessment
        title = a.title if a else "Continue assessment"
        add(
            action_type="TAKE_ASSESSMENT" if (a and a.assessment_type not in ("ADAPTIVE_PRACTICE", "TOPIC_REASSESSMENT")) else (
                "ADAPTIVE_PRACTICE" if a and a.assessment_type == "ADAPTIVE_PRACTICE" else "TAKE_REASSESSMENT"
            ),
            title=f"Continue: {title}",
            reason="You have an unfinished assessment attempt.",
            priority="CRITICAL",
            source="P0-011",
            hierarchy_group="UNFINISHED",
            mandatory=True,
            target_topic_id=a.topic_id if a else None,
            target_subject_id=a.subject_id if a else None,
            resource_reference={"kind": "attempt", "id": att.id, "attempt_id": att.id, "assessment_id": att.assessment_id},
            outcome="Submitting the attempt lets the assessment engine evaluate your work.",
            explanation=_explain(
                what=f"Continue {title}",
                why="You started this assessment and have not finished it.",
                source="P0-011 Assessment Engine (open attempt)",
                outcome="Your attempt will be evaluated by the existing assessment engine.",
                action_type="TAKE_ASSESSMENT",
            ),
        )

    resume = snapshot.get("lecture_resume")
    if resume:
        step = resume.get("current_step_index", 0)
        total = resume.get("step_count")
        step_label = f"Step {step + 1}" + (f" of {total}" if total else "")
        add(
            action_type="CONTINUE_LEARNING",
            title=f"Continue learning: {resume.get('title') or 'AI Lecturer'}",
            reason=f"You paused an AI Lecturer session ({step_label}).",
            priority="HIGH",
            source="P0-013",
            hierarchy_group="UNFINISHED",
            mandatory=False,
            target_topic_id=resume.get("topic_id"),
            target_subject_id=resume.get("subject_id"),
            resource_reference={
                "kind": "session",
                "id": resume.get("session_id"),
                "session_id": resume.get("session_id"),
                "current_step_index": step,
                "step_count": total,
            },
            explanation=_explain(
                what=f"Continue {resume.get('title') or 'your lesson'}",
                why=f"Your last activity was AI Lecturer — {step_label}.",
                source="P0-013 Learning Session progress",
                outcome="Session progress continues from where you stopped. Mastery is not granted by watching alone.",
                action_type="CONTINUE_LEARNING",
            ),
        )

    for sess in snapshot.get("open_sessions") or []:
        if resume and sess.id == resume.get("session_id"):
            continue
        if sess.status not in ("IN_PROGRESS", "PAUSED", "READY"):
            continue
        add(
            action_type="CONTINUE_LEARNING",
            title=f"Continue session: {sess.title}",
            reason="You have an unfinished learning session.",
            priority="HIGH",
            source="P0-013",
            hierarchy_group="UNFINISHED",
            target_topic_id=sess.topic_id,
            target_subject_id=sess.subject_id,
            resource_reference={"kind": "session", "id": sess.id, "session_id": sess.id},
            explanation=_explain(
                what=f"Continue {sess.title}",
                why="This learning session is still open.",
                source="P0-013 Learning Sessions",
                outcome="You will resume the existing session; no new academic score is created here.",
                action_type="CONTINUE_LEARNING",
            ),
        )

    # 2. Active remediation
    for iv in snapshot.get("open_interventions") or []:
        gap = iv.gap_snapshot or {}
        topic_id = iv.learning_gap.scope_id if iv.learning_gap and iv.learning_gap.scope_type == "TOPIC" else gap.get("scope_id")
        add(
            action_type="COMPLETE_REMEDIATION",
            title=f"Complete remedial learning: {gap.get('scope_name') or _topic_name(topics.get(topic_id), topic_id)}",
            reason=iv.priority_explanation or "An assigned remedial intervention is still open.",
            priority="CRITICAL" if (gap.get("classification") == "CRITICAL_GAP" or gap.get("severity") == "critical") else "HIGH",
            source="P0-014",
            hierarchy_group="REMEDIATION",
            mandatory=True,
            target_topic_id=topic_id,
            resource_reference={
                "kind": "intervention",
                "id": iv.id,
                "intervention_id": iv.id,
                "session_id": iv.learning_session_id,
            },
            explanation=_explain(
                what="Complete your assigned remedial learning",
                why="Faculty assigned a remedial intervention for an identified learning gap.",
                source="P0-014 Remedial Learning",
                outcome="Completing the intervention is recorded by the remedial engine. Mastery still requires practice/reassessment (P0-015).",
                action_type="COMPLETE_REMEDIATION",
            ),
        )

    warnings = snapshot.get("warnings") or []
    warn_by_topic: Dict[int, Dict[str, Any]] = {}
    max_severity = None
    sev_rank = {"URGENT_ATTENTION": 0, "ATTENTION_REQUIRED": 1, "WATCH": 2, "INFO": 3}
    for w in warnings:
        tid = w.get("topic_id")
        if tid is not None:
            prev = warn_by_topic.get(tid)
            if prev is None or sev_rank.get(w.get("severity"), 9) < sev_rank.get(prev.get("severity"), 9):
                warn_by_topic[tid] = w
        if max_severity is None or sev_rank.get(w.get("severity"), 9) < sev_rank.get(max_severity, 9):
            max_severity = w.get("severity")

    # Per-topic orchestration from P0-015 status + P0-012 gaps + P0-016 warnings
    active_gaps = snapshot.get("active_gaps") or []
    gaps_by_topic = {
        g.scope_id: g
        for g in active_gaps
        if g.scope_type == "TOPIC" and g.scope_id is not None
    }

    assigned_topic_ids = set()
    for iv in snapshot.get("open_interventions") or []:
        gap = iv.gap_snapshot or {}
        sid = gap.get("scope_id")
        if iv.learning_gap and iv.learning_gap.scope_type == "TOPIC":
            sid = iv.learning_gap.scope_id
        if sid:
            assigned_topic_ids.add(sid)

    for topic_id, state in states.items():
        topic = topics.get(topic_id)
        name = _topic_name(topic, topic_id)
        gap = gaps_by_topic.get(topic_id)
        warn = warn_by_topic.get(topic_id)
        status = state.status

        if status == "REASSESSMENT_PENDING":
            asg = next(
                (
                    a
                    for a in (snapshot.get("assignments") or [])
                    if a.topic_id == topic_id and a.purpose == "REASSESSMENT" and a.status in ("READY", "IN_PROGRESS")
                ),
                None,
            )
            add(
                action_type="TAKE_REASSESSMENT",
                title=f"Complete reassessment: {name}",
                reason="A reassessment is pending for this topic.",
                priority="HIGH",
                source="P0-015",
                hierarchy_group="UNFINISHED",
                mandatory=True,
                target_topic_id=topic_id,
                resource_reference={
                    "kind": "assignment",
                    "id": asg.id if asg else None,
                    "assessment_id": asg.assessment_id if asg else None,
                },
                explanation=_explain(
                    what=f"Take the pending reassessment for {name}",
                    why="P0-015 marked this topic as reassessment pending.",
                    source="P0-015 TopicMasteryState.REASSESSMENT_PENDING",
                    outcome="The mastery engine will decide mastery from the reassessment result.",
                    action_type="TAKE_REASSESSMENT",
                ),
            )

        if status in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED"):
            if topic_id not in assigned_topic_ids:
                add(
                    action_type="REVIEW_TOPIC",
                    title=f"Review and get support: {name}",
                    reason="Authoritative mastery status indicates this topic needs remediation.",
                    priority="HIGH",
                    source="P0-015",
                    hierarchy_group="PERSISTENT_GAP" if gap else "TOPIC_LEARNING",
                    target_topic_id=topic_id,
                    explanation=_explain(
                        what=f"Review {name} and follow a remedial path",
                        why=f"Mastery status is {status}."
                        + (" An active learning gap is also recorded." if gap else ""),
                        source="P0-015 TopicMasteryState" + (" + P0-012 LearningGap" if gap else ""),
                        outcome="After review, use practice. P0-015 decides reassessment readiness.",
                        action_type="REVIEW_TOPIC",
                    ),
                )
                add(
                    action_type="SELF_STUDY",
                    title=f"Study {name} myself",
                    reason="Self-study is an allowed learning route alongside AI Lecturer and expert support.",
                    priority="OPTIONAL",
                    source="P0-017",
                    hierarchy_group="ENRICHMENT",
                    target_topic_id=topic_id,
                    explanation=_explain(
                        what=f"Study {name} on your own",
                        why="You may choose self-study; academic requirements still apply.",
                        source="P0-017 student choice (status from P0-015)",
                        outcome="Self-study does not grant mastery. Practice evidence still updates P0-015.",
                        action_type="SELF_STUDY",
                    ),
                )
                add(
                    action_type="START_AI_LECTURE",
                    title=f"Learn {name} with AI Lecturer",
                    reason="AI Lecturer is an available learning route for topics that need support.",
                    priority="MEDIUM",
                    source="P0-013",
                    hierarchy_group="TOPIC_LEARNING",
                    target_topic_id=topic_id,
                    explanation=_explain(
                        what=f"Start an AI Lecturer lesson on {name}",
                        why="This topic needs learning support. You are not required to use AI-only learning.",
                        source="P0-013 / P0-015",
                        outcome="Lesson progress is tracked in the learning session. Mastery is not automatic.",
                        action_type="START_AI_LECTURE",
                    ),
                )

        failed = status in ("NEEDS_REMEDIATION", "NEEDS_PRACTICE", "MASTERY_REGRESSED") and any(
            e.event_type == "REASSESSMENT_FAILED"
            for e in (snapshot.get("events_by_topic") or {}).get(topic_id, [])
        )
        if failed:
            add(
                action_type="RETRY",
                title=f"Targeted practice after reassessment: {name}",
                reason="A previous reassessment did not establish mastery. Follow-up practice is recommended.",
                priority="HIGH",
                source="P0-015",
                hierarchy_group="FAILED_REASSESSMENT",
                target_topic_id=topic_id,
                explanation=_explain(
                    what=f"Return to targeted practice for {name}",
                    why="P0-015 recorded a failed reassessment. The orchestrator does not override that result.",
                    source="P0-015 MasteryEvent.REASSESSMENT_FAILED",
                    outcome="Further practice and/or remediation; P0-015 will re-evaluate readiness later.",
                    action_type="RETRY",
                ),
            )

        if gap and topic_id not in assigned_topic_ids and status not in ("MASTERED",):
            persistent = False
            if warn and warn.get("code") == "PERSISTENT_LEARNING_GAP":
                persistent = True
            add(
                action_type="COMPLETE_REMEDIATION" if persistent else "REVIEW_TOPIC",
                title=f"{'Address persistent gap' if persistent else 'Work on learning gap'}: {name}",
                reason=f"Active learning gap ({gap.classification}) on this topic."
                + (" Persistence signal from early-warning analytics." if persistent else " No remedial assignment yet."),
                priority="HIGH" if persistent or gap.classification == "CRITICAL_GAP" else "MEDIUM",
                source="P0-012" if not persistent else "P0-016",
                hierarchy_group="PERSISTENT_GAP" if persistent else "TOPIC_LEARNING",
                target_topic_id=topic_id,
                resource_reference={"kind": "learning_gap", "id": gap.id, "learning_gap_id": gap.id},
                explanation=_explain(
                    what=f"Follow a remedial path for {name}",
                    why=f"P0-012 classified this topic as {gap.classification}."
                    + (" P0-016 flagged it as persistent." if persistent else " No P0-014 intervention is assigned yet."),
                    source="P0-012 LearningGap" + (" + P0-016" if persistent else ""),
                    outcome="Faculty may assign a P0-014 intervention. Practice still goes through P0-015.",
                    action_type="REVIEW_TOPIC",
                ),
            )

        if status in ("NEEDS_PRACTICE", "LEARNING"):
            asg = next(
                (
                    a
                    for a in (snapshot.get("assignments") or [])
                    if a.topic_id == topic_id and a.purpose == "PRACTICE" and a.status in ("READY", "IN_PROGRESS")
                ),
                None,
            )
            add(
                action_type="ADAPTIVE_PRACTICE",
                title=f"Adaptive practice: {name}",
                reason="Practice is required to build mastery evidence."
                if status == "NEEDS_PRACTICE"
                else "Practice accuracy is improving, but mastery has not yet been established.",
                priority="HIGH" if status == "NEEDS_PRACTICE" else "MEDIUM",
                source="P0-015",
                hierarchy_group="ADAPTIVE_PRACTICE",
                target_topic_id=topic_id,
                resource_reference={
                    "kind": "assignment",
                    "id": asg.id if asg else None,
                    "assessment_id": asg.assessment_id if asg else None,
                },
                explanation=_explain(
                    what=f"Practice {name}",
                    why=(
                        "P0-015 status is NEEDS_PRACTICE."
                        if status == "NEEDS_PRACTICE"
                        else "You completed learning/practice progress, but mastery is not yet established."
                    ),
                    source="P0-015 TopicMasteryState",
                    outcome="Practice evidence updates mastery status in P0-015.",
                    action_type="ADAPTIVE_PRACTICE",
                ),
            )

        if status == "READY_FOR_REASSESSMENT":
            add(
                action_type="TAKE_REASSESSMENT",
                title=f"Reassessment: {name}",
                reason="You are eligible for topic reassessment.",
                priority="HIGH",
                source="P0-015",
                hierarchy_group="REASSESSMENT",
                target_topic_id=topic_id,
                explanation=_explain(
                    what=f"Take reassessment for {name}",
                    why="P0-015 marked this topic READY_FOR_REASSESSMENT.",
                    source="P0-015 TopicMasteryState.READY_FOR_REASSESSMENT",
                    outcome="The mastery engine will set MASTERED or return you to practice/remediation.",
                    action_type="TAKE_REASSESSMENT",
                ),
            )

        if status in ("NOT_ASSESSED", "LEARNING") and topic_id not in assigned_topic_ids:
            if status == "NOT_ASSESSED":
                add(
                    action_type="START_AI_LECTURE",
                    title=f"Learn {name}",
                    reason="This topic has not been assessed yet. Start learning when you are ready.",
                    priority="MEDIUM",
                    source="P0-015",
                    hierarchy_group="TOPIC_LEARNING",
                    target_topic_id=topic_id,
                    explanation=_explain(
                        what=f"Start learning {name}",
                        why="No mastery evidence is recorded yet for this topic.",
                        source="P0-015 TopicMasteryState.NOT_ASSESSED",
                        outcome="Choose AI Lecturer, self-study, or practice. Mastery is decided later by P0-015.",
                        action_type="START_AI_LECTURE",
                    ),
                )
                add(
                    action_type="SELF_STUDY",
                    title=f"Study {name} myself",
                    reason="Self-study is available; you are not forced into AI-only learning.",
                    priority="OPTIONAL",
                    source="P0-017",
                    hierarchy_group="ENRICHMENT",
                    target_topic_id=topic_id,
                )
                add(
                    action_type="PRACTICE",
                    title=f"Practice questions: {name}",
                    reason="Practice is an available route even before a full lesson.",
                    priority="OPTIONAL",
                    source="P0-015",
                    hierarchy_group="ENRICHMENT",
                    target_topic_id=topic_id,
                )

        if warn and warn.get("severity") == "WATCH" and status not in ("MASTERED",):
            add(
                action_type="ADAPTIVE_PRACTICE",
                title=f"Keep practicing: {name}",
                reason=warn.get("reason") or "Early-warning status is WATCH — extra practice is encouraged.",
                priority="MEDIUM",
                source="P0-016",
                hierarchy_group="ADAPTIVE_PRACTICE",
                target_topic_id=topic_id,
                explanation=_explain(
                    what=f"Practice {name}",
                    why=warn.get("reason") or "P0-016 issued a WATCH signal.",
                    source="P0-016 Early Warning (WATCH)",
                    outcome="Practice updates P0-015. The warning is not recalculated here.",
                    action_type="ADAPTIVE_PRACTICE",
                ),
            )

        if warn and warn.get("severity") == "ATTENTION_REQUIRED":
            add(
                action_type="REVIEW_TOPIC",
                title=f"Targeted support: {name}",
                reason=warn.get("reason") or "This topic needs targeted learning support.",
                priority="HIGH",
                source="P0-016",
                hierarchy_group="PERSISTENT_GAP",
                target_topic_id=topic_id,
                explanation=_explain(
                    what=f"Get targeted support for {name}",
                    why=warn.get("reason") or "P0-016 attention required.",
                    source="P0-016 Early Warning (ATTENTION_REQUIRED)",
                    outcome="Follow remedial/practice routes. Warning severity is owned by P0-016.",
                    action_type="REVIEW_TOPIC",
                ),
            )

        if warn and warn.get("severity") == "URGENT_ATTENTION":
            add(
                action_type="HUMAN_EXPERT_SUPPORT",
                title=f"Request faculty / expert support: {name}",
                reason=warn.get("reason") or "Urgent attention signal — human support is appropriate.",
                priority="CRITICAL",
                source="P0-016",
                hierarchy_group="PERSISTENT_GAP",
                target_topic_id=topic_id,
                explanation=_explain(
                    what=f"Ask for human subject-expert support on {name}",
                    why=warn.get("reason") or "P0-016 issued URGENT_ATTENTION.",
                    source="P0-016 Early Warning (URGENT_ATTENTION)",
                    outcome="Faculty can assign a P0-014 intervention or P0-013 session. Mastery is unchanged here.",
                    action_type="HUMAN_EXPERT_SUPPORT",
                ),
            )
            add(
                action_type="WAIT_FOR_FACULTY_ACTION",
                title="Waiting for faculty follow-up",
                reason="Urgent support has been recommended. Faculty may assign an intervention.",
                priority="HIGH",
                source="P0-016",
                hierarchy_group="PERSISTENT_GAP",
                mandatory=False,
                target_topic_id=topic_id,
            )

        if status == "MASTERED":
            add(
                action_type="MOVE_TO_NEXT_TOPIC",
                title=f"{name} mastered — continue",
                reason="This topic is mastered. Continue to the next eligible topic.",
                priority="LOW",
                source="P0-015",
                hierarchy_group="CURRICULUM",
                target_topic_id=topic_id,
                explanation=_explain(
                    what="Move forward in the course",
                    why=f"{name} is MASTERED according to P0-015.",
                    source="P0-015 TopicMasteryState.MASTERED",
                    outcome="The next eligible topic becomes the focus. Mastery is not recalculated here.",
                    action_type="MOVE_TO_NEXT_TOPIC",
                ),
            )

    # Upcoming published assessments (real due_date / available_until only)
    now = snapshot.get("now") or _utcnow()
    for a in snapshot.get("published_assessments") or []:
        if a.assessment_type in ("ADAPTIVE_PRACTICE", "TOPIC_REASSESSMENT"):
            continue
        if a.status != "PUBLISHED":
            continue
        due = a.due_date or a.available_until
        if due is None:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now - timedelta(days=1):
            continue
        overdue = due < now
        add(
            action_type="TAKE_ASSESSMENT",
            title=f"{'Overdue' if overdue else 'Upcoming'} assessment: {a.title}",
            reason=("This published assessment is overdue." if overdue else "A published assessment is coming up."),
            priority="CRITICAL" if overdue else "HIGH",
            source="P0-011",
            hierarchy_group="UNFINISHED" if overdue else "CURRICULUM",
            mandatory=True,
            target_topic_id=a.topic_id,
            target_subject_id=a.subject_id,
            resource_reference={"kind": "assessment", "id": a.id, "assessment_id": a.id},
            explanation=_explain(
                what=f"Take {a.title}",
                why="The assessment is published"
                + (" and past its due date." if overdue else " with a scheduled deadline."),
                source="P0-011 published assessment schedule",
                outcome="The assessment engine records the attempt. Deadlines are not invented by P0-017.",
                action_type="TAKE_ASSESSMENT",
            ),
        )

    next_topic = snapshot.get("next_topic")
    if next_topic and next_topic.id not in states:
        add(
            action_type="START_AI_LECTURE",
            title=f"Begin next topic: {next_topic.name}",
            reason="Continue the course with the next topic in the curriculum order.",
            priority="MEDIUM",
            source="P0-017",
            hierarchy_group="CURRICULUM",
            target_topic_id=next_topic.id,
            target_subject_id=next_topic.subject_id,
            explanation=_explain(
                what=f"Start {next_topic.name}",
                why="Earlier topics are mastered or this is the next curriculum topic.",
                source="Existing course/subject/topic structure",
                outcome="You may learn with AI Lecturer, self-study, or practice.",
                action_type="START_AI_LECTURE",
            ),
        )
        add(
            action_type="SELF_STUDY",
            title=f"Study {next_topic.name} myself",
            reason="Self-study is available for the next curriculum topic.",
            priority="OPTIONAL",
            source="P0-017",
            hierarchy_group="ENRICHMENT",
            target_topic_id=next_topic.id,
            target_subject_id=next_topic.subject_id,
        )

    # Faculty-sourced open recommendations already in snapshot (re-emitted as candidates so they persist)
    for fa in snapshot.get("faculty_actions") or []:
        item = {
            "action_type": fa.action_type,
            "title": fa.title,
            "description": fa.description or fa.reason,
            "reason": fa.reason,
            "priority": fa.priority,
            "source": "FACULTY",
            "hierarchy_group": fa.hierarchy_group
            or (
                "REMEDIATION"
                if fa.action_type in ("HUMAN_EXPERT_SUPPORT", "COMPLETE_REMEDIATION", "WAIT_FOR_FACULTY_ACTION")
                else "TOPIC_LEARNING"
            ),
            "hierarchy_rank": LEARNING_HIERARCHY_RANKS.get(
                fa.hierarchy_group
                or (
                    "REMEDIATION"
                    if fa.action_type in ("HUMAN_EXPERT_SUPPORT", "COMPLETE_REMEDIATION", "WAIT_FOR_FACULTY_ACTION")
                    else "TOPIC_LEARNING"
                ),
                6,
            ),
            "target_course_id": course_id,
            "target_subject_id": fa.target_subject_id,
            "target_topic_id": fa.target_topic_id,
            "target_unit_id": None,
            "resource_reference": fa.resource_reference or {"kind": "faculty", "id": fa.id},
            "prerequisites": fa.prerequisites or [],
            "mandatory": bool(fa.mandatory),
            "explanation": fa.explanation
            or _explain(
                what=fa.title,
                why=fa.reason,
                source="Faculty recommendation (does not change mastery)",
                outcome="This is advisory unless it points at an existing required activity.",
                action_type=fa.action_type,
            ),
            "href": _href_for(fa.action_type, fa.resource_reference),
            "stable_key": fa.stable_key,
        }
        candidates.append(item)

    # Deduplicate by stable_key keeping highest precedence
    by_key: Dict[str, Dict[str, Any]] = {}
    for c in _sort_candidates(candidates):
        if c["stable_key"] not in by_key:
            by_key[c["stable_key"]] = c
    return _sort_candidates(list(by_key.values()))


def select_next_best(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ordered = _sort_candidates(candidates)
    return ordered[0] if ordered else None


def alternatives_for(primary: Optional[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not primary:
        return []
    alts = []
    for c in _sort_candidates(candidates):
        if c["stable_key"] == primary["stable_key"]:
            continue
        same_topic = c.get("target_topic_id") == primary.get("target_topic_id")
        optional_or_route = c["action_type"] in (
            "SELF_STUDY",
            "START_AI_LECTURE",
            "WATCH_LECTURE",
            "ASK_LECTURER",
            "PRACTICE",
            "REVIEW_TOPIC",
            "ADAPTIVE_PRACTICE",
        )
        if same_topic and optional_or_route:
            alts.append(c)
        if len(alts) >= 4:
            break
    return alts


def daily_plan_from(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simple ordered plan from existing recommendations — not a timetable optimizer."""
    plan = []
    seen_types = set()
    durations = {
        "REVIEW_TOPIC": 15,
        "START_AI_LECTURE": 20,
        "WATCH_LECTURE": 20,
        "CONTINUE_LEARNING": 20,
        "ADAPTIVE_PRACTICE": 15,
        "PRACTICE": 15,
        "COMPLETE_REMEDIATION": 25,
        "TAKE_REASSESSMENT": None,
        "TAKE_ASSESSMENT": None,
        "RETRY": 15,
        "SELF_STUDY": 20,
    }
    for c in _sort_candidates(candidates):
        if c["action_type"] in seen_types:
            continue
        if c["priority"] == "OPTIONAL" and len(plan) >= 3:
            continue
        seen_types.add(c["action_type"])
        mins = durations.get(c["action_type"], 15)
        plan.append(
            {
                "order": len(plan) + 1,
                "action_type": c["action_type"],
                "title": c["title"],
                "minutes": mins,
                "when": "when eligible" if mins is None else f"{mins} min",
                "reason": c["reason"],
                "priority": c["priority"],
                "mandatory": c.get("mandatory"),
            }
        )
        if len(plan) >= 4:
            break
    return plan


def derive_journey_state(snapshot: Dict[str, Any], primary: Optional[Dict[str, Any]]) -> str:
    states = list((snapshot.get("states") or {}).values())
    if not states and not snapshot.get("topics"):
        return "NOT_STARTED"
    if states and all(s.status == "MASTERED" for s in states) and not primary:
        return "MASTERED"
    if primary and primary["action_type"] == "WAIT_FOR_FACULTY_ACTION":
        return "BLOCKED"
    if primary and primary["action_type"] == "TAKE_REASSESSMENT":
        return "READY_FOR_REASSESSMENT"
    if primary and primary["action_type"] == "TAKE_ASSESSMENT":
        return "READY_FOR_ASSESSMENT"
    if any(s.status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED", "REMEDIATION_IN_PROGRESS") for s in states):
        return "NEEDS_SUPPORT"
    if primary and primary.get("mandatory"):
        return "WAITING_FOR_ACTION"
    if primary:
        return "IN_PROGRESS"
    if states and all(s.status == "MASTERED" for s in states):
        return "COMPLETED"
    return "NOT_STARTED"


def progress_counts(states: List[models.TopicMasteryState]) -> Dict[str, int]:
    mastered = sum(1 for s in states if s.status == "MASTERED")
    support = sum(
        1
        for s in states
        if s.status in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED")
    )
    improving = sum(1 for s in states if s.status in ("LEARNING", "READY_FOR_REASSESSMENT", "NEEDS_PRACTICE"))
    return {
        "mastered": mastered,
        "improving": improving,
        "needs_support": support,
        "total": len(states),
    }


# ---------------------------------------------------------------------------
# Snapshot gather
# ---------------------------------------------------------------------------

def _course_topics(db: Session, course_id: int) -> List[models.Topic]:
    subjects = db.query(models.Subject).filter(models.Subject.course_id == course_id).all()
    sids = [s.id for s in subjects]
    if not sids:
        return []
    return (
        db.query(models.Topic)
        .filter(models.Topic.subject_id.in_(sids))
        .order_by(models.Topic.subject_id, models.Topic.id)
        .all()
    )


def gather_snapshot(db: Session, *, student_id: int, course_id: int) -> Dict[str, Any]:
    topics_list = _course_topics(db, course_id)
    topics = {t.id: t for t in topics_list}
    states_rows = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
        )
        .all()
    )
    states = {s.topic_id: s for s in states_rows}

    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
        )
        .all()
    )
    active_gaps = [
        g
        for g in gaps
        if not _gap_resolved(g) and g.classification in ("WEAK", "CRITICAL_GAP", "DEVELOPING")
    ]

    interventions = (
        db.query(models.RemedialIntervention)
        .filter(
            models.RemedialIntervention.course_id == course_id,
            models.RemedialIntervention.status.in_(("ASSIGNED", "IN_PROGRESS", "DRAFT")),
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
    open_interventions = [
        iv
        for iv in interventions
        if iv.student_id == student_id or (iv.group_id and iv.group_id in member_gids)
    ]

    parts = (
        db.query(models.LearningSessionParticipant)
        .filter(models.LearningSessionParticipant.user_id == student_id)
        .all()
    )
    session_ids = [p.session_id for p in parts]
    open_sessions = []
    if session_ids:
        open_sessions = (
            db.query(models.LearningSession)
            .filter(
                models.LearningSession.id.in_(session_ids),
                models.LearningSession.course_id == course_id,
                models.LearningSession.status.in_(("READY", "IN_PROGRESS", "PAUSED")),
            )
            .all()
        )

    lecture_resume = None
    for sess in open_sessions:
        ev = (
            db.query(models.LearningEvidence)
            .filter(
                models.LearningEvidence.session_id == sess.id,
                models.LearningEvidence.user_id == student_id,
                models.LearningEvidence.event_type.in_(
                    ("TEACHING_STEP_REACHED", "TEACHING_PAUSED", "TEACHING_OPENED", "TEACHING_RESUMED")
                ),
            )
            .order_by(models.LearningEvidence.id.desc())
            .first()
        )
        if not ev:
            continue
        payload = ev.payload or {}
        lecture_resume = {
            "session_id": sess.id,
            "title": sess.title,
            "topic_id": sess.topic_id,
            "subject_id": sess.subject_id,
            "current_step_index": int(payload.get("current_step_index") or 0),
            "lecture_status": payload.get("status"),
            "step_count": (payload.get("step_count") or (sess.outcome_summary or {}).get("step_count")),
        }
        break

    open_attempts = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.student_id == student_id,
            models.AssessmentAttempt.course_id == course_id,
            models.AssessmentAttempt.status.in_(("NOT_STARTED", "IN_PROGRESS")),
        )
        .all()
    )

    assignments = (
        db.query(models.AdaptivePracticeAssignment)
        .filter(
            models.AdaptivePracticeAssignment.student_id == student_id,
            models.AdaptivePracticeAssignment.course_id == course_id,
        )
        .order_by(models.AdaptivePracticeAssignment.created_at.desc())
        .all()
    )

    events = (
        db.query(models.MasteryEvent)
        .filter(
            models.MasteryEvent.student_id == student_id,
            models.MasteryEvent.course_id == course_id,
        )
        .order_by(models.MasteryEvent.created_at.asc())
        .all()
    )
    events_by_topic: Dict[int, List[models.MasteryEvent]] = {}
    for e in events:
        events_by_topic.setdefault(e.topic_id, []).append(e)

    warnings = ew.evaluate_student_warnings(db, student_id=student_id, course_id=course_id)

    published_assessments = (
        db.query(models.Assessment)
        .filter(
            models.Assessment.course_id == course_id,
            models.Assessment.status == "PUBLISHED",
        )
        .all()
    )

    mastered_ids = {tid for tid, s in states.items() if s.status == "MASTERED"}
    next_topic = next((t for t in topics_list if t.id not in mastered_ids), None)

    faculty_actions = (
        db.query(models.LearningJourneyAction)
        .filter(
            models.LearningJourneyAction.student_id == student_id,
            models.LearningJourneyAction.course_id == course_id,
            models.LearningJourneyAction.source == "FACULTY",
            models.LearningJourneyAction.status.in_(LEARNING_ACTION_OPEN_STATUSES),
        )
        .all()
    )

    recent_events = sorted(events, key=lambda x: x.created_at or _utcnow(), reverse=True)[:8]

    return {
        "course_id": course_id,
        "student_id": student_id,
        "topics": topics,
        "topics_list": topics_list,
        "states": states,
        "active_gaps": active_gaps,
        "open_interventions": open_interventions,
        "open_sessions": open_sessions,
        "lecture_resume": lecture_resume,
        "open_attempts": open_attempts,
        "assignments": assignments,
        "events_by_topic": events_by_topic,
        "recent_events": recent_events,
        "warnings": warnings,
        "published_assessments": published_assessments,
        "next_topic": next_topic,
        "faculty_actions": faculty_actions,
        "now": _utcnow(),
    }


def action_to_dict(row: models.LearningJourneyAction) -> Dict[str, Any]:
    ref = row.resource_reference or {}
    return {
        "action_id": row.id,
        "action_type": row.action_type,
        "title": row.title,
        "description": row.description,
        "reason": row.reason,
        "priority": row.priority,
        "status": row.status,
        "source": row.source,
        "target_course": row.course_id,
        "target_subject": row.target_subject_id,
        "target_unit": None,
        "target_topic": row.target_topic_id,
        "resource_reference": ref,
        "prerequisites": row.prerequisites or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "mandatory": row.mandatory,
        "hierarchy_group": row.hierarchy_group,
        "explanation": row.explanation,
        "href": _href_for(row.action_type, ref),
        "chosen_alternative": row.chosen_alternative,
        "stable_key": row.stable_key,
    }


def _persist_candidates(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    candidates: List[Dict[str, Any]],
) -> List[models.LearningJourneyAction]:
    existing = (
        db.query(models.LearningJourneyAction)
        .filter(
            models.LearningJourneyAction.student_id == student_id,
            models.LearningJourneyAction.course_id == course_id,
            models.LearningJourneyAction.status.in_(LEARNING_ACTION_OPEN_STATUSES),
        )
        .all()
    )
    by_key = {r.stable_key: r for r in existing}
    keep = set()
    now = _utcnow()
    for c in candidates:
        key = c["stable_key"]
        keep.add(key)
        row = by_key.get(key)
        if row:
            if row.status in ("STARTED", "IN_PROGRESS", "ACCEPTED"):
                row.reason = c["reason"]
                row.priority = c["priority"]
                row.explanation = c["explanation"]
                row.title = c["title"]
                row.resource_reference = c.get("resource_reference")
            else:
                row.title = c["title"]
                row.description = c.get("description")
                row.reason = c["reason"]
                row.priority = c["priority"]
                row.source = c["source"]
                row.hierarchy_group = c["hierarchy_group"]
                row.target_subject_id = c.get("target_subject_id")
                row.target_topic_id = c.get("target_topic_id")
                row.resource_reference = c.get("resource_reference")
                row.prerequisites = c.get("prerequisites")
                row.explanation = c.get("explanation")
                row.mandatory = bool(c.get("mandatory"))
            continue
        row = models.LearningJourneyAction(
            student_id=student_id,
            course_id=course_id,
            stable_key=key,
            action_type=c["action_type"],
            title=c["title"],
            description=c.get("description"),
            reason=c["reason"],
            priority=c["priority"],
            status="RECOMMENDED",
            source=c["source"],
            hierarchy_group=c["hierarchy_group"],
            target_subject_id=c.get("target_subject_id"),
            target_topic_id=c.get("target_topic_id"),
            resource_reference=c.get("resource_reference"),
            prerequisites=c.get("prerequisites"),
            explanation=c.get("explanation"),
            mandatory=bool(c.get("mandatory")),
        )
        db.add(row)
        by_key[key] = row
    for row in existing:
        if row.stable_key not in keep and row.source != "FACULTY":
            row.status = "SUPERSEDED"
            row.completed_at = now
    db.commit()
    open_rows = (
        db.query(models.LearningJourneyAction)
        .filter(
            models.LearningJourneyAction.student_id == student_id,
            models.LearningJourneyAction.course_id == course_id,
            models.LearningJourneyAction.status.in_(LEARNING_ACTION_OPEN_STATUSES),
        )
        .all()
    )
    return open_rows


def _maybe_notify(db: Session, *, student_id: int, course_id: int, primary: Optional[models.LearningJourneyAction]) -> None:
    if not primary:
        return
    if primary.last_notified_at:
        return
    if primary.priority not in ("CRITICAL", "HIGH"):
        return
    event = "NEXT_LEARNING_ACTION_AVAILABLE"
    severity = "INFO"
    if primary.action_type == "TAKE_REASSESSMENT":
        event = "REASSESSMENT_READY"
    elif primary.action_type == "COMPLETE_REMEDIATION":
        event = "REMEDIAL_ACTION_REQUIRED"
        severity = "WARNING"
    elif primary.action_type in ("HUMAN_EXPERT_SUPPORT", "WAIT_FOR_FACULTY_ACTION"):
        event = "SUPPORT_RECOMMENDED"
        severity = "WARNING"
    elif primary.action_type == "MOVE_TO_NEXT_TOPIC" and primary.source == "P0-015":
        event = "MASTERY_MILESTONE"
        severity = "SUCCESS"
    notif_svc.emit_event(
        db,
        event=event,
        title=primary.title,
        message=primary.reason,
        student_id=student_id,
        course_id=course_id,
        severity=severity,
        source_module="ORCHESTRATOR",
        link_path="/learning-journey/me",
        payload={
            "action_id": primary.id,
            "action_type": primary.action_type,
            "source": primary.source,
        },
        channels=["IN_APP"],
        dispatch=True,
    )
    primary.last_notified_at = _utcnow()
    db.commit()


def _timeline(snapshot: Dict[str, Any], primary: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for t in snapshot.get("topics_list") or []:
        state = (snapshot.get("states") or {}).get(t.id)
        status = state.status if state else "NOT_ASSESSED"
        marker = "upcoming"
        if status == "MASTERED":
            marker = "mastered"
        elif status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED", "REMEDIATION_IN_PROGRESS"):
            marker = "needs_support"
        elif state:
            marker = "learning"
        if primary and primary.get("target_topic_id") == t.id:
            marker = "current" if marker != "needs_support" else "needs_support"
        rows.append(
            {
                "topic_id": t.id,
                "topic_name": t.name,
                "subject_id": t.subject_id,
                "mastery_status": status,
                "indicator": state.indicator if state else "GRAY",
                "marker": marker,
                "source_of_truth": "P0-015_TopicMasteryState" if state else "curriculum",
            }
        )
    return rows


def build_journey(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    persist: bool = True,
    notify: bool = True,
) -> Dict[str, Any]:
    _authorize_student_view(db, actor, student_id, course_id)
    if (actor.role or "").lower() == "student":
        _require_enrollment(db, student_id, course_id)
    snapshot = gather_snapshot(db, student_id=student_id, course_id=course_id)
    candidates = build_candidates(snapshot)
    primary_c = select_next_best(candidates)
    alts = alternatives_for(primary_c, candidates)
    plan = daily_plan_from(candidates)
    journey_state = derive_journey_state(snapshot, primary_c)

    open_rows: List[models.LearningJourneyAction] = []
    if persist:
        open_rows = _persist_candidates(db, student_id=student_id, course_id=course_id, candidates=candidates)
        open_sorted = sorted(
            open_rows,
            key=lambda r: (
                LEARNING_HIERARCHY_RANKS.get(r.hierarchy_group or "", 99),
                _priority_rank(r.priority),
                r.id,
            ),
        )
        primary_row = open_sorted[0] if open_sorted else None
        if notify:
            _maybe_notify(db, student_id=student_id, course_id=course_id, primary=primary_row)
        primary_out = action_to_dict(primary_row) if primary_row else None
        if primary_out and primary_c:
            primary_out["explanation"] = primary_row.explanation or primary_c.get("explanation")
        actions_out = [action_to_dict(r) for r in open_sorted]
        alt_out = []
        if primary_row:
            for c in alts:
                match = next((r for r in open_sorted if r.stable_key == c["stable_key"]), None)
                if match:
                    alt_out.append(action_to_dict(match))
    else:
        primary_out = {**primary_c, "action_id": None} if primary_c else None
        actions_out = [{**c, "action_id": None, "status": "RECOMMENDED"} for c in candidates]
        alt_out = alts

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    student = db.query(models.User).filter(models.User.id == student_id).first()
    states_list = list((snapshot.get("states") or {}).values())
    resume = snapshot.get("lecture_resume")

    current_topic = None
    if primary_out and primary_out.get("target_topic"):
        t = snapshot["topics"].get(primary_out["target_topic"])
        if t:
            current_topic = {"id": t.id, "name": t.name, "subject_id": t.subject_id}

    return {
        "student_id": student_id,
        "student_name": student.name if student else None,
        "course_id": course_id,
        "course_title": course.title if course else None,
        "journey_state": journey_state,
        "current_topic": current_topic,
        "next_best_action": primary_out,
        "alternatives": alt_out,
        "actions": actions_out[:20],
        "daily_plan": plan,
        "journey": _timeline(snapshot, primary_c),
        "progress": progress_counts(states_list),
        "resume": resume,
        "attention": [
            {
                "code": w.get("code"),
                "severity": w.get("severity"),
                "topic_id": w.get("topic_id"),
                "topic_name": w.get("topic_name"),
                "title": w.get("title"),
                "reason": w.get("reason"),
                "source": "P0-016",
            }
            for w in (snapshot.get("warnings") or [])[:8]
        ],
        "recent_activity": [
            {
                "event_type": e.event_type,
                "topic_id": e.topic_id,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in snapshot.get("recent_events") or []
        ],
        "learning_modes": [
            "AI_LECTURER",
            "SELF_STUDY",
            "ADAPTIVE_PRACTICE",
            "HUMAN_SUBJECT_EXPERT",
            "REMEDIAL_LEARNING",
            "ASSESSMENT",
            "REASSESSMENT",
        ],
        "authority_note": (
            "P0-017 selects the next action from P0-012 gaps, P0-013 sessions, "
            "P0-014 interventions, P0-015 mastery, and P0-016 warnings. "
            "It does not recalculate academic intelligence."
        ),
        "curriculum_note": (
            "Curriculum uses existing Course → Subject → Topic (no separate Unit model)."
        ),
    }


def list_my_actions(db: Session, actor: models.User, *, course_id: int) -> Dict[str, Any]:
    data = build_journey(db, actor, student_id=actor.id, course_id=course_id)
    return {
        "course_id": course_id,
        "next_best_action": data["next_best_action"],
        "actions": data["actions"],
        "alternatives": data["alternatives"],
    }


def progress_view(db: Session, actor: models.User, *, student_id: int, course_id: int) -> Dict[str, Any]:
    data = build_journey(db, actor, student_id=student_id, course_id=course_id, notify=False)
    return {
        "student_id": student_id,
        "course_id": course_id,
        "journey_state": data["journey_state"],
        "progress": data["progress"],
        "journey": data["journey"],
        "resume": data["resume"],
        "recent_activity": data["recent_activity"],
    }


def _get_own_action(db: Session, actor: models.User, action_id: int) -> models.LearningJourneyAction:
    row = db.query(models.LearningJourneyAction).filter(models.LearningJourneyAction.id == action_id).first()
    if not row:
        raise _http(404, "Learning action not found")
    role = (actor.role or "").lower()
    if role == "student" and row.student_id != actor.id:
        raise _http(403, "Students may only manage their own learning actions")
    if role != "student":
        _authorize_student_view(db, actor, row.student_id, row.course_id)
    return row


def start_action(db: Session, actor: models.User, action_id: int) -> Dict[str, Any]:
    row = _get_own_action(db, actor, action_id)
    if row.status not in LEARNING_ACTION_OPEN_STATUSES:
        raise _http(409, f"Action cannot be started from status {row.status}")
    row.status = "IN_PROGRESS"
    row.started_at = row.started_at or _utcnow()
    extra: Dict[str, Any] = {}
    ref = dict(row.resource_reference or {})
    student_id = row.student_id
    if row.action_type in ("ADAPTIVE_PRACTICE", "PRACTICE", "RETRY") and not ref.get("assessment_id") and row.target_topic_id:
        started = mastery.start_practice(
            db,
            actor,
            student_id=student_id,
            course_id=row.course_id,
            topic_id=row.target_topic_id,
        )
        ref["assessment_id"] = started.get("assessment_id")
        ref["assignment_id"] = started.get("assignment_id")
        ref["kind"] = "assignment"
        extra["launch"] = started
    elif row.action_type == "TAKE_REASSESSMENT" and not ref.get("assessment_id") and row.target_topic_id:
        started = mastery.start_reassessment(
            db,
            actor,
            student_id=student_id,
            course_id=row.course_id,
            topic_id=row.target_topic_id,
        )
        ref["assessment_id"] = started.get("assessment_id")
        ref["assignment_id"] = started.get("assignment_id")
        extra["launch"] = started
    row.resource_reference = ref
    db.commit()
    db.refresh(row)
    out = action_to_dict(row)
    out.update(extra)
    out["href"] = _href_for(row.action_type, ref)
    return out


def complete_action(db: Session, actor: models.User, action_id: int) -> Dict[str, Any]:
    row = _get_own_action(db, actor, action_id)
    if row.status in ("COMPLETED", "SUPERSEDED", "CANCELLED", "EXPIRED"):
        raise _http(409, f"Action already closed ({row.status})")
    row.status = "COMPLETED"
    row.completed_at = _utcnow()
    db.commit()
    db.refresh(row)
    return action_to_dict(row)


def dismiss_action(db: Session, actor: models.User, action_id: int) -> Dict[str, Any]:
    row = _get_own_action(db, actor, action_id)
    if row.mandatory:
        raise _http(409, "Mandatory academic actions cannot be dismissed")
    if row.status in ("COMPLETED", "SUPERSEDED", "CANCELLED", "EXPIRED"):
        raise _http(409, f"Action already closed ({row.status})")
    row.status = "CANCELLED"
    row.completed_at = _utcnow()
    db.commit()
    db.refresh(row)
    return action_to_dict(row)


def choose_action(db: Session, actor: models.User, action_id: int, *, choice_action_id: Optional[int] = None) -> Dict[str, Any]:
    """Student accepts an alternative recommended action for the same topic."""
    primary = _get_own_action(db, actor, action_id)
    if not choice_action_id:
        primary.status = "ACCEPTED"
        db.commit()
        db.refresh(primary)
        return action_to_dict(primary)
    choice = _get_own_action(db, actor, choice_action_id)
    if choice.student_id != primary.student_id or choice.course_id != primary.course_id:
        raise _http(403, "Choice must belong to the same student journey")
    if primary.mandatory and choice.id != primary.id:
        raise _http(409, "A mandatory action is still required; you may also start an optional route.")
    choice.status = "ACCEPTED"
    primary.chosen_alternative = choice.action_type
    if not primary.mandatory:
        primary.status = "SUPERSEDED"
        primary.completed_at = _utcnow()
    db.commit()
    db.refresh(choice)
    return action_to_dict(choice)


def faculty_students(db: Session, actor: models.User, *, course_id: int) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    enrollments = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.course_id == course_id)
        .all()
    )
    rows = []
    for enr in enrollments:
        data = build_journey(
            db, actor, student_id=enr.student_id, course_id=course_id, persist=True, notify=False
        )
        nba = data.get("next_best_action") or {}
        rows.append(
            {
                "student_id": data["student_id"],
                "student_name": data["student_name"],
                "journey_state": data["journey_state"],
                "current_topic": data.get("current_topic"),
                "next_action_type": nba.get("action_type"),
                "next_action_title": nba.get("title"),
                "reason": nba.get("reason"),
                "priority": nba.get("priority"),
                "source": nba.get("source"),
                "support_needed": data["journey_state"] in ("NEEDS_SUPPORT", "BLOCKED")
                or (nba.get("action_type") in ("HUMAN_EXPERT_SUPPORT", "COMPLETE_REMEDIATION", "WAIT_FOR_FACULTY_ACTION")),
                "progress": data["progress"],
            }
        )
    return {"course_id": course_id, "students": rows}


def faculty_student(db: Session, actor: models.User, *, student_id: int, course_id: int) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    data = build_journey(db, actor, student_id=student_id, course_id=course_id, persist=True, notify=False)
    data["faculty_actions_available"] = [
        "Recommend HUMAN_EXPERT_SUPPORT (advisory)",
        "Assign intervention via P0-014 /remedial/interventions/individual",
        "Create/manage learning session via P0-013",
        "Approve reassessment via P0-015",
    ]
    data["cannot"] = [
        "Change mastery status",
        "Change learning-gap classification",
        "Change assessment scores",
    ]
    return data


def faculty_recommend(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    action_type: str,
    topic_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    if action_type not in LEARNING_ACTION_TYPES:
        raise _http(422, "Unknown action type")
    if action_type in ("TAKE_REASSESSMENT",) or action_type.startswith("TAKE_"):
        # Faculty must use existing engines for academic starts
        pass
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first() if topic_id else None
    title = f"Faculty recommendation: {action_type.replace('_', ' ').title()}"
    if topic:
        title = f"{title} — {topic.name}"
    why = reason or "Faculty recommended this learning action. Mastery and scores are unchanged."
    key = _stable_key(action_type=action_type, topic_id=topic_id, ref_kind="faculty", ref_id=actor.id)
    existing = (
        db.query(models.LearningJourneyAction)
        .filter(
            models.LearningJourneyAction.student_id == student_id,
            models.LearningJourneyAction.course_id == course_id,
            models.LearningJourneyAction.stable_key == key,
            models.LearningJourneyAction.status.in_(LEARNING_ACTION_OPEN_STATUSES),
        )
        .first()
    )
    if existing:
        existing.reason = why
        existing.title = title
        existing.description = why
        db.commit()
        db.refresh(existing)
        return action_to_dict(existing)
    row = models.LearningJourneyAction(
        student_id=student_id,
        course_id=course_id,
        stable_key=key,
        action_type=action_type,
        title=title,
        description=why,
        reason=why,
        priority="HIGH" if action_type in ("HUMAN_EXPERT_SUPPORT", "COMPLETE_REMEDIATION") else "MEDIUM",
        status="RECOMMENDED",
        source="FACULTY",
        hierarchy_group="REMEDIATION" if action_type in ("HUMAN_EXPERT_SUPPORT", "COMPLETE_REMEDIATION") else "TOPIC_LEARNING",
        target_subject_id=topic.subject_id if topic else None,
        target_topic_id=topic_id,
        resource_reference={"kind": "faculty", "faculty_id": actor.id},
        explanation=_explain(
            what=title,
            why=why,
            source="Faculty (advisory — does not override P0-015/P0-012)",
            outcome="Use existing P0-013/P0-014 tools to assign real sessions or interventions.",
            action_type=action_type,
        ),
        mandatory=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    notif_svc.emit_event(
        db,
        event="SUPPORT_RECOMMENDED" if action_type == "HUMAN_EXPERT_SUPPORT" else "NEXT_LEARNING_ACTION_AVAILABLE",
        title=title,
        message=why,
        student_id=student_id,
        course_id=course_id,
        source_module="ORCHESTRATOR",
        link_path="/learning-journey/me",
        channels=["IN_APP"],
    )
    return action_to_dict(row)


def admin_overview(db: Session, actor: models.User, *, course_id: Optional[int] = None) -> Dict[str, Any]:
    _authorize_admin(actor)
    q = db.query(models.LearningJourneyAction).filter(
        models.LearningJourneyAction.status.in_(LEARNING_ACTION_OPEN_STATUSES)
    )
    if course_id is not None:
        q = q.filter(models.LearningJourneyAction.course_id == course_id)
    actions = q.all()
    waiting_support = [
        a for a in actions if a.action_type in ("HUMAN_EXPERT_SUPPORT", "WAIT_FOR_FACULTY_ACTION")
    ]
    remedial_demand = [a for a in actions if a.action_type == "COMPLETE_REMEDIATION"]
    topic_counts: Dict[Tuple[int, Optional[int]], int] = {}
    for a in actions:
        if a.action_type in ("COMPLETE_REMEDIATION", "REVIEW_TOPIC", "HUMAN_EXPERT_SUPPORT", "RETRY"):
            key = (a.course_id, a.target_topic_id)
            topic_counts[key] = topic_counts.get(key, 0) + 1
    bottlenecks = []
    for (cid, tid), n in sorted(topic_counts.items(), key=lambda x: -x[1])[:15]:
        t = db.query(models.Topic).filter(models.Topic.id == tid).first() if tid else None
        bottlenecks.append({"course_id": cid, "topic_id": tid, "topic_name": t.name if t else None, "open_support_actions": n})

    mq = db.query(models.TopicMasteryState)
    if course_id is not None:
        mq = mq.filter(models.TopicMasteryState.course_id == course_id)
    states = mq.all()
    mastered = sum(1 for s in states if s.status == "MASTERED")
    unresolved = sum(1 for s in states if s.status not in ("MASTERED", "NOT_ASSESSED"))

    return {
        "course_id": course_id,
        "students_waiting_for_support": len({a.student_id for a in waiting_support}),
        "remedial_learning_demand": len({a.student_id for a in remedial_demand}),
        "unresolved_learning_journeys": unresolved,
        "mastered_topic_states": mastered,
        "open_orchestration_actions": len(actions),
        "topic_bottlenecks": bottlenecks,
        "note": "Aggregates only. Individual student journeys are not listed here.",
    }
