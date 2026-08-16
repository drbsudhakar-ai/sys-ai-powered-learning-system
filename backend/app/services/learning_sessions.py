"""P0-013.1 Learning Session domain service — persistence + auth foundation.

Full HTTP API surface is deferred to P0-013.2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app import models
from app.academic_auth import (
    can_access_course_questions,
    is_admin,
    is_course_coordinator,
    is_subject_expert,
)
from app.constants import (
    LEARNING_ACTIVITY_SCOPES,
    LEARNING_ACTIVITY_STATUSES,
    LEARNING_ACTIVITY_TYPES,
    LEARNING_EVIDENCE_EVENT_TYPES,
    LEARNING_OBJECTIVE_STATUSES,
    LEARNING_PARTICIPANT_ROLES,
    LEARNING_PARTICIPANT_STATUSES,
    LEARNING_SESSION_MODES,
    LEARNING_SESSION_STATUSES,
    LEARNING_SESSION_TRANSITIONS,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


# ---------- Authorization foundation ----------

def can_manage_learning_sessions(
    db: Session,
    user: models.User,
    *,
    course_id: int,
    subject_id: Optional[int] = None,
) -> bool:
    if is_admin(user):
        return True
    if is_course_coordinator(db, user, course_id):
        return True
    if subject_id is not None and is_subject_expert(db, user, subject_id):
        return True
    if can_access_course_questions(db, user, course_id) and (user.role or "").lower() == "faculty":
        return True
    return False


def require_manage_session_scope(
    db: Session,
    user: models.User,
    *,
    course_id: int,
    subject_id: Optional[int] = None,
) -> None:
    if not can_manage_learning_sessions(db, user, course_id=course_id, subject_id=subject_id):
        raise _http(status.HTTP_403_FORBIDDEN, "Insufficient permissions for learning session scope")


def is_session_participant(db: Session, session_id: int, user_id: int) -> bool:
    return (
        db.query(models.LearningSessionParticipant)
        .filter(
            models.LearningSessionParticipant.session_id == session_id,
            models.LearningSessionParticipant.user_id == user_id,
            models.LearningSessionParticipant.status.notin_(("REMOVED",)),
        )
        .first()
        is not None
    )


def can_view_session(db: Session, user: models.User, session: models.LearningSession) -> bool:
    if is_admin(user):
        return True
    if session.created_by == user.id or session.facilitator_id == user.id:
        return True
    if can_manage_learning_sessions(
        db, user, course_id=session.course_id, subject_id=session.subject_id
    ):
        return True
    if is_session_participant(db, session.id, user.id):
        return True
    return False


def require_view_session(db: Session, user: models.User, session: models.LearningSession) -> None:
    if not can_view_session(db, user, session):
        raise _http(status.HTTP_403_FORBIDDEN, "Not authorized to view this learning session")


def require_manage_session(db: Session, user: models.User, session: models.LearningSession) -> None:
    if is_admin(user):
        return
    if session.created_by == user.id or session.facilitator_id == user.id:
        return
    require_manage_session_scope(
        db, user, course_id=session.course_id, subject_id=session.subject_id
    )


def _can_manage(db: Session, user: models.User, session: models.LearningSession) -> bool:
    try:
        require_manage_session(db, user, session)
        return True
    except HTTPException:
        return False


def get_participant_row(
    db: Session, session_id: int, *, user_id: Optional[int] = None, participant_id: Optional[int] = None
) -> Optional[models.LearningSessionParticipant]:
    q = db.query(models.LearningSessionParticipant).filter(
        models.LearningSessionParticipant.session_id == session_id,
        models.LearningSessionParticipant.status.notin_(("REMOVED",)),
    )
    if participant_id is not None:
        q = q.filter(models.LearningSessionParticipant.id == participant_id)
    if user_id is not None:
        q = q.filter(models.LearningSessionParticipant.user_id == user_id)
    return q.first()


def activity_visible_to_user(
    db: Session,
    user: models.User,
    session: models.LearningSession,
    activity: models.LearningSessionActivity,
) -> bool:
    """COMMON activities are visible to all authorized session viewers.
    PARTICIPANT_SPECIFIC activities are visible only to the target student (or managers).
    """
    if not can_view_session(db, user, session):
        return False
    if _can_manage(db, user, session) or is_admin(user):
        return True
    if (activity.scope or "COMMON").upper() == "COMMON":
        return True
    # Participant-specific: only the assigned participant
    if not activity.participant_id:
        return False
    part = get_participant_row(db, session.id, participant_id=activity.participant_id)
    return bool(part and part.user_id == user.id)


def list_activities_for_user(
    db: Session,
    actor: models.User,
    session_id: int,
) -> List[models.LearningSessionActivity]:
    session = get_session(db, session_id)
    require_view_session(db, actor, session)
    activities = sorted(session.activities or [], key=lambda a: (a.sequence, a.id))
    return [a for a in activities if activity_visible_to_user(db, actor, session, a)]


def assigned_activities_for_participant(
    session: models.LearningSession,
    participant: models.LearningSessionParticipant,
) -> List[models.LearningSessionActivity]:
    out = []
    for a in sorted(session.activities or [], key=lambda x: (x.sequence, x.id)):
        scope = (a.scope or "COMMON").upper()
        if scope == "COMMON":
            out.append(a)
        elif scope == "PARTICIPANT_SPECIFIC" and a.participant_id == participant.id:
            out.append(a)
    return out


def compute_participant_progress(
    db: Session,
    session: models.LearningSession,
    participant: models.LearningSessionParticipant,
) -> Dict[str, Any]:
    """Participant progress from assigned activities + evidence (not session status)."""
    assigned = assigned_activities_for_participant(session, participant)
    evidence = (
        db.query(models.LearningEvidence)
        .filter(
            models.LearningEvidence.session_id == session.id,
            models.LearningEvidence.user_id == participant.user_id,
            models.LearningEvidence.event_type == "ACTIVITY_COMPLETED",
        )
        .all()
    )
    completed_ids = {e.activity_id for e in evidence if e.activity_id}
    completed = [a for a in assigned if a.id in completed_ids]
    total = len(assigned)
    done = len(completed)
    pct = round(100.0 * done / total, 2) if total else 0.0
    if participant.status == "COMPLETED" or (total > 0 and done == total):
        progress_status = "COMPLETED"
    elif done > 0 or participant.status == "ACTIVE":
        progress_status = "IN_PROGRESS"
    elif participant.status in ("INVITED", "JOINED"):
        progress_status = participant.status
    else:
        progress_status = participant.status
    return {
        "participant_id": participant.id,
        "user_id": participant.user_id,
        "role": participant.role,
        "participant_status": participant.status,
        "progress_status": progress_status,
        "assigned_activities": total,
        "completed_activities": done,
        "percent_complete": pct,
        "session_status": session.status,
        "note": "Participant progress is independent of session-level lifecycle status.",
    }


def list_session_progress(
    db: Session,
    actor: models.User,
    session_id: int,
) -> Dict[str, Any]:
    session = get_session(db, session_id)
    require_view_session(db, actor, session)
    students = [
        p
        for p in (session.participants or [])
        if p.role == "STUDENT" and p.status != "REMOVED"
    ]
    if _can_manage(db, actor, session) or is_admin(actor):
        progress = [compute_participant_progress(db, session, p) for p in students]
    else:
        mine = [p for p in students if p.user_id == actor.id]
        progress = [compute_participant_progress(db, session, p) for p in mine]
    return {
        "session_id": session.id,
        "mode": session.mode,
        "session_status": session.status,
        "participants": progress,
    }


def set_participant_status(
    db: Session,
    actor: models.User,
    session_id: int,
    participant_id: int,
    new_status: str,
) -> models.LearningSessionParticipant:
    session = get_session(db, session_id)
    new_status = (new_status or "").upper()
    if new_status not in LEARNING_PARTICIPANT_STATUSES:
        raise _http(422, f"Invalid participant status: {new_status}")
    row = (
        db.query(models.LearningSessionParticipant)
        .filter(
            models.LearningSessionParticipant.id == participant_id,
            models.LearningSessionParticipant.session_id == session_id,
        )
        .first()
    )
    if not row or row.status == "REMOVED":
        raise _http(404, "Participant not found")
    # Self can JOIN/ACTIVE/COMPLETED own row; managers can set any
    if actor.id == row.user_id:
        if new_status not in ("JOINED", "ACTIVE", "COMPLETED", "LEFT"):
            raise _http(403, "Students may only update their own participation status")
    else:
        require_manage_session(db, actor, session)
    row.status = new_status
    if new_status in ("JOINED", "ACTIVE") and not row.joined_at:
        row.joined_at = _utcnow()
    if new_status in ("LEFT", "REMOVED"):
        row.left_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


# ---------- Validation helpers ----------

def _validate_mode(mode: str) -> str:
    mode = (mode or "").upper()
    if mode not in LEARNING_SESSION_MODES:
        raise _http(422, f"Invalid session mode: {mode}")
    return mode


def _validate_academic_refs(
    db: Session,
    *,
    course_id: int,
    subject_id: Optional[int],
    topic_id: Optional[int],
    subtopic_id: Optional[int],
) -> None:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise _http(404, "Course not found")
    if subject_id is not None:
        subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
        if not subject:
            raise _http(404, "Subject not found")
        if subject.course_id and subject.course_id != course_id:
            raise _http(422, "Subject does not belong to course")
    if topic_id is not None:
        topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
        if not topic:
            raise _http(404, "Topic not found")
        if subject_id is not None and topic.subject_id != subject_id:
            raise _http(422, "Topic does not belong to subject")
    if subtopic_id is not None:
        sub = db.query(models.Subtopic).filter(models.Subtopic.id == subtopic_id).first()
        if not sub:
            raise _http(404, "Subtopic not found")
        if topic_id is not None and sub.topic_id != topic_id:
            raise _http(422, "Subtopic does not belong to topic")


# ---------- Domain operations ----------

def create_session(
    db: Session,
    actor: models.User,
    *,
    title: str,
    course_id: int,
    mode: str,
    description: Optional[str] = None,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    subtopic_id: Optional[int] = None,
    facilitator_id: Optional[int] = None,
    scheduled_start: Optional[datetime] = None,
    scheduled_end: Optional[datetime] = None,
    primary_student_id: Optional[int] = None,
) -> models.LearningSession:
    mode = _validate_mode(mode)
    require_manage_session_scope(db, actor, course_id=course_id, subject_id=subject_id)
    _validate_academic_refs(
        db,
        course_id=course_id,
        subject_id=subject_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
    )

    if mode == "INDIVIDUAL" and not primary_student_id:
        raise _http(422, "INDIVIDUAL sessions require primary_student_id")

    if primary_student_id:
        student = (
            db.query(models.User)
            .filter(models.User.id == primary_student_id, models.User.role == "student")
            .first()
        )
        if not student:
            raise _http(404, "Student not found")
        enrolled = (
            db.query(models.StudentCourseEnrollment)
            .filter(
                models.StudentCourseEnrollment.student_id == primary_student_id,
                models.StudentCourseEnrollment.course_id == course_id,
            )
            .first()
        )
        if not enrolled:
            raise _http(403, "Student is not enrolled in this course")

    session = models.LearningSession(
        title=title.strip(),
        description=description,
        mode=mode,
        status="DRAFT",
        course_id=course_id,
        subject_id=subject_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        facilitator_id=facilitator_id or actor.id,
        created_by=actor.id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
    )
    db.add(session)
    db.flush()

    # Facilitator as participant
    fac_id = facilitator_id or actor.id
    db.add(
        models.LearningSessionParticipant(
            session_id=session.id,
            user_id=fac_id,
            role="TEACHER" if is_admin(actor) else "FACILITATOR",
            status="JOINED",
            joined_at=_utcnow(),
        )
    )

    if primary_student_id:
        db.add(
            models.LearningSessionParticipant(
                session_id=session.id,
                user_id=primary_student_id,
                role="STUDENT",
                status="INVITED",
            )
        )

    db.commit()
    db.refresh(session)
    return get_session(db, session.id)


def get_session(db: Session, session_id: int) -> models.LearningSession:
    session = (
        db.query(models.LearningSession)
        .options(
            joinedload(models.LearningSession.participants),
            joinedload(models.LearningSession.objectives),
            joinedload(models.LearningSession.activities),
        )
        .filter(models.LearningSession.id == session_id)
        .first()
    )
    if not session:
        raise _http(404, "Learning session not found")
    return session


def list_sessions_for_user(
    db: Session,
    user: models.User,
    *,
    course_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    mode: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[models.LearningSession]:
    q = db.query(models.LearningSession)
    if course_id is not None:
        q = q.filter(models.LearningSession.course_id == course_id)
    if subject_id is not None:
        q = q.filter(models.LearningSession.subject_id == subject_id)
    if topic_id is not None:
        q = q.filter(models.LearningSession.topic_id == topic_id)
    if mode:
        q = q.filter(models.LearningSession.mode == _validate_mode(mode))
    if status_filter:
        if status_filter not in LEARNING_SESSION_STATUSES:
            raise _http(422, "Invalid status filter")
        q = q.filter(models.LearningSession.status == status_filter)

    sessions = q.order_by(models.LearningSession.id.desc()).limit(200).all()
    return [s for s in sessions if can_view_session(db, user, s)]


def update_session(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    subject_id: Optional[int] = ...,
    topic_id: Optional[int] = ...,
    subtopic_id: Optional[int] = ...,
    scheduled_start: Optional[datetime] = ...,
    scheduled_end: Optional[datetime] = ...,
) -> models.LearningSession:
    """Update mutable metadata. Ellipsis means field not provided."""
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if session.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        raise _http(400, "Cannot modify a closed session")

    if title is not None:
        if not str(title).strip():
            raise _http(422, "Title cannot be empty")
        session.title = str(title).strip()
    if description is not None:
        session.description = description

    new_subject = session.subject_id if subject_id is ... else subject_id
    new_topic = session.topic_id if topic_id is ... else topic_id
    new_subtopic = session.subtopic_id if subtopic_id is ... else subtopic_id
    if subject_id is not ... or topic_id is not ... or subtopic_id is not ...:
        _validate_academic_refs(
            db,
            course_id=session.course_id,
            subject_id=new_subject,
            topic_id=new_topic,
            subtopic_id=new_subtopic,
        )
        # Changing subject scope still requires manage rights on new subject
        if subject_id is not ... and subject_id != session.subject_id:
            require_manage_session_scope(
                db, actor, course_id=session.course_id, subject_id=subject_id
            )
        session.subject_id = new_subject
        session.topic_id = new_topic
        session.subtopic_id = new_subtopic

    if scheduled_start is not ...:
        session.scheduled_start = scheduled_start
    if scheduled_end is not ...:
        session.scheduled_end = scheduled_end

    db.commit()
    return get_session(db, session.id)


def transition_status(
    db: Session,
    actor: models.User,
    session_id: int,
    new_status: str,
) -> models.LearningSession:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    new_status = (new_status or "").upper()
    if new_status not in LEARNING_SESSION_STATUSES:
        raise _http(422, f"Invalid status: {new_status}")
    allowed = LEARNING_SESSION_TRANSITIONS.get(session.status, set())
    if new_status not in allowed:
        raise _http(
            422,
            f"Invalid lifecycle transition: {session.status} → {new_status}",
        )
    now = _utcnow()
    if new_status == "IN_PROGRESS" and not session.actual_start:
        session.actual_start = now
        record_evidence(
            db,
            actor,
            session_id=session.id,
            event_type="SESSION_STARTED",
            user_id=actor.id,
            commit=False,
        )
    if new_status == "PAUSED":
        record_evidence(
            db,
            actor,
            session_id=session.id,
            event_type="SESSION_PAUSED",
            user_id=actor.id,
            commit=False,
        )
    if new_status == "COMPLETED":
        session.actual_end = now
        record_evidence(
            db,
            actor,
            session_id=session.id,
            event_type="SESSION_COMPLETED",
            user_id=actor.id,
            commit=False,
        )
    session.status = new_status
    db.commit()
    return get_session(db, session.id)


def start_session_flow(db: Session, actor: models.User, session_id: int) -> models.LearningSession:
    """Move session into IN_PROGRESS via valid intermediate states if needed."""
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if session.status == "IN_PROGRESS":
        return session
    if session.status == "DRAFT":
        session = transition_status(db, actor, session_id, "READY")
    elif session.status == "SCHEDULED":
        session = transition_status(db, actor, session_id, "READY")
    if session.status == "READY":
        return transition_status(db, actor, session_id, "IN_PROGRESS")
    if session.status == "PAUSED":
        return transition_status(db, actor, session_id, "IN_PROGRESS")
    raise _http(422, f"Cannot start session from status {session.status}")


def add_participant(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    user_id: int,
    role: str = "STUDENT",
) -> models.LearningSessionParticipant:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    role = (role or "STUDENT").upper()
    if role not in LEARNING_PARTICIPANT_ROLES:
        raise _http(422, f"Invalid participant role: {role}")

    if session.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        raise _http(400, "Cannot add participants to a closed session")

    if session.mode == "INDIVIDUAL" and role == "STUDENT":
        existing_students = (
            db.query(models.LearningSessionParticipant)
            .filter(
                models.LearningSessionParticipant.session_id == session_id,
                models.LearningSessionParticipant.role == "STUDENT",
                models.LearningSessionParticipant.status.notin_(("REMOVED",)),
            )
            .count()
        )
        if existing_students >= 1:
            raise _http(422, "INDIVIDUAL sessions allow only one student participant")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise _http(404, "User not found")
    if role == "STUDENT":
        if (user.role or "").lower() != "student":
            raise _http(422, "Participant role STUDENT requires a student user")
        enrolled = (
            db.query(models.StudentCourseEnrollment)
            .filter(
                models.StudentCourseEnrollment.student_id == user_id,
                models.StudentCourseEnrollment.course_id == session.course_id,
            )
            .first()
        )
        if not enrolled:
            raise _http(403, "Student is not enrolled in this course")

    dup = (
        db.query(models.LearningSessionParticipant)
        .filter(
            models.LearningSessionParticipant.session_id == session_id,
            models.LearningSessionParticipant.user_id == user_id,
        )
        .first()
    )
    if dup:
        if dup.status == "REMOVED":
            dup.status = "INVITED"
            dup.role = role
            dup.left_at = None
            db.commit()
            db.refresh(dup)
            return dup
        raise _http(409, "Participant already in session")

    row = models.LearningSessionParticipant(
        session_id=session_id,
        user_id=user_id,
        role=role,
        status="INVITED",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remove_participant(
    db: Session,
    actor: models.User,
    session_id: int,
    participant_id: int,
) -> models.LearningSessionParticipant:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    row = (
        db.query(models.LearningSessionParticipant)
        .filter(
            models.LearningSessionParticipant.id == participant_id,
            models.LearningSessionParticipant.session_id == session_id,
        )
        .first()
    )
    if not row:
        raise _http(404, "Participant not found")
    row.status = "REMOVED"
    row.left_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def add_objective(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    statement: str,
    sequence: Optional[int] = None,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    subtopic_id: Optional[int] = None,
    concept_tag: Optional[str] = None,
) -> models.LearningSessionObjective:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if not (statement or "").strip():
        raise _http(422, "Objective statement is required")
    _validate_academic_refs(
        db,
        course_id=session.course_id,
        subject_id=subject_id or session.subject_id,
        topic_id=topic_id or session.topic_id,
        subtopic_id=subtopic_id,
    )
    if sequence is None:
        sequence = (
            db.query(models.LearningSessionObjective)
            .filter(models.LearningSessionObjective.session_id == session_id)
            .count()
            + 1
        )
    row = models.LearningSessionObjective(
        session_id=session_id,
        statement=statement.strip(),
        sequence=sequence,
        status="PENDING",
        subject_id=subject_id or session.subject_id,
        topic_id=topic_id or session.topic_id,
        subtopic_id=subtopic_id,
        concept_tag=concept_tag,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_objective(
    db: Session,
    actor: models.User,
    session_id: int,
    objective_id: int,
) -> Dict[str, Any]:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if session.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        raise _http(400, "Cannot modify objectives on a closed session")
    row = (
        db.query(models.LearningSessionObjective)
        .filter(
            models.LearningSessionObjective.id == objective_id,
            models.LearningSessionObjective.session_id == session_id,
        )
        .first()
    )
    if not row:
        raise _http(404, "Objective not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "objective_id": objective_id}


def update_activity(
    db: Session,
    actor: models.User,
    session_id: int,
    activity_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = ...,
    sequence: Optional[int] = None,
    status_value: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = ...,
) -> models.LearningSessionActivity:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if session.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        raise _http(400, "Cannot modify activities on a closed session")
    row = (
        db.query(models.LearningSessionActivity)
        .filter(
            models.LearningSessionActivity.id == activity_id,
            models.LearningSessionActivity.session_id == session_id,
        )
        .first()
    )
    if not row:
        raise _http(404, "Activity not found")
    if title is not None:
        if not str(title).strip():
            raise _http(422, "Title cannot be empty")
        row.title = str(title).strip()
    if description is not ...:
        row.description = description
    if sequence is not None:
        clash = (
            db.query(models.LearningSessionActivity)
            .filter(
                models.LearningSessionActivity.session_id == session_id,
                models.LearningSessionActivity.sequence == sequence,
                models.LearningSessionActivity.id != activity_id,
            )
            .first()
        )
        if clash:
            raise _http(422, f"Activity sequence conflict: sequence {sequence} already used")
        row.sequence = sequence
    if status_value is not None:
        status_value = status_value.upper()
        if status_value not in LEARNING_ACTIVITY_STATUSES:
            raise _http(422, f"Invalid activity status: {status_value}")
        row.status = status_value
    if payload is not ...:
        row.payload = payload
    db.commit()
    db.refresh(row)
    return row


def delete_activity(
    db: Session,
    actor: models.User,
    session_id: int,
    activity_id: int,
) -> Dict[str, Any]:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    if session.status in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        raise _http(400, "Cannot modify activities on a closed session")
    row = (
        db.query(models.LearningSessionActivity)
        .filter(
            models.LearningSessionActivity.id == activity_id,
            models.LearningSessionActivity.session_id == session_id,
        )
        .first()
    )
    if not row:
        raise _http(404, "Activity not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "activity_id": activity_id}


def list_evidence(
    db: Session,
    actor: models.User,
    session_id: int,
) -> List[models.LearningEvidence]:
    session = get_session(db, session_id)
    require_view_session(db, actor, session)
    rows = (
        db.query(models.LearningEvidence)
        .filter(models.LearningEvidence.session_id == session_id)
        .order_by(models.LearningEvidence.id.desc())
        .limit(500)
        .all()
    )
    # Students only see their own evidence unless they can manage the session
    can_manage = False
    try:
        require_manage_session(db, actor, session)
        can_manage = True
    except HTTPException:
        can_manage = False
    if can_manage or is_admin(actor):
        return rows
    return [r for r in rows if r.user_id == actor.id]


def add_activity(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    activity_type: str,
    title: str,
    description: Optional[str] = None,
    sequence: Optional[int] = None,
    scope: str = "COMMON",
    participant_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    assessment_id: Optional[int] = None,
) -> models.LearningSessionActivity:
    session = get_session(db, session_id)
    require_manage_session(db, actor, session)
    activity_type = (activity_type or "").upper()
    if activity_type not in LEARNING_ACTIVITY_TYPES:
        raise _http(422, f"Invalid activity type: {activity_type}")
    scope = (scope or "COMMON").upper()
    if scope not in LEARNING_ACTIVITY_SCOPES:
        raise _http(422, f"Invalid activity scope: {scope}")
    if not (title or "").strip():
        raise _http(422, "Activity title is required")

    if scope == "PARTICIPANT_SPECIFIC":
        if not participant_id:
            raise _http(422, "PARTICIPANT_SPECIFIC activities require participant_id")
        part = (
            db.query(models.LearningSessionParticipant)
            .filter(
                models.LearningSessionParticipant.id == participant_id,
                models.LearningSessionParticipant.session_id == session_id,
            )
            .first()
        )
        if not part or part.status == "REMOVED":
            raise _http(404, "Participant not found in session")
        if part.role != "STUDENT":
            raise _http(422, "Participant-specific activities must target a STUDENT participant")
        if session.mode == "INDIVIDUAL":
            student_parts = [
                p
                for p in (session.participants or [])
                if p.role == "STUDENT" and p.status != "REMOVED"
            ]
            if not student_parts or part.id != student_parts[0].id:
                raise _http(422, "INDIVIDUAL session activities must target the session student")
    else:
        # COMMON scope
        if participant_id is not None:
            raise _http(422, "COMMON activities cannot target a specific participant")

    if assessment_id is not None:
        a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
        if not a:
            raise _http(404, "Assessment not found")
        if a.course_id != session.course_id:
            raise _http(422, "Assessment does not belong to session course")

    if sequence is None:
        sequence = (
            db.query(models.LearningSessionActivity)
            .filter(models.LearningSessionActivity.session_id == session_id)
            .count()
            + 1
        )
    else:
        clash = (
            db.query(models.LearningSessionActivity)
            .filter(
                models.LearningSessionActivity.session_id == session_id,
                models.LearningSessionActivity.sequence == sequence,
            )
            .first()
        )
        if clash:
            raise _http(422, f"Activity sequence conflict: sequence {sequence} already used")

    row = models.LearningSessionActivity(
        session_id=session_id,
        activity_type=activity_type,
        title=title.strip(),
        description=description,
        sequence=sequence,
        scope=scope,
        participant_id=participant_id if scope == "PARTICIPANT_SPECIFIC" else None,
        status="PENDING",
        payload=payload,
        assessment_id=assessment_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_evidence(
    db: Session,
    actor: models.User,
    *,
    session_id: int,
    event_type: str,
    user_id: Optional[int] = None,
    participant_id: Optional[int] = None,
    activity_id: Optional[int] = None,
    objective_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    commit: bool = True,
) -> models.LearningEvidence:
    session = get_session(db, session_id)
    subject_uid = user_id or actor.id
    if not can_view_session(db, actor, session):
        raise _http(403, "Not authorized to record evidence for this session")
    if actor.id != subject_uid and not _can_manage(db, actor, session):
        raise _http(403, "Cannot record evidence for another user")

    event_type = (event_type or "").upper()
    if event_type not in LEARNING_EVIDENCE_EVENT_TYPES:
        raise _http(422, f"Invalid evidence event type: {event_type}")

    act = None
    if activity_id is not None:
        act = (
            db.query(models.LearningSessionActivity)
            .filter(
                models.LearningSessionActivity.id == activity_id,
                models.LearningSessionActivity.session_id == session_id,
            )
            .first()
        )
        if not act:
            raise _http(404, "Activity not found in session")
        # Subject must be allowed to see / act on this activity
        subject_user = db.query(models.User).filter(models.User.id == subject_uid).first()
        if not subject_user or not activity_visible_to_user(db, subject_user, session, act):
            raise _http(403, "Evidence subject cannot access this activity")
        if (act.scope or "").upper() == "PARTICIPANT_SPECIFIC":
            target = get_participant_row(db, session_id, participant_id=act.participant_id)
            if not target or target.user_id != subject_uid:
                raise _http(403, "Cannot record evidence on another participant's activity")

    if objective_id is not None:
        obj = (
            db.query(models.LearningSessionObjective)
            .filter(
                models.LearningSessionObjective.id == objective_id,
                models.LearningSessionObjective.session_id == session_id,
            )
            .first()
        )
        if not obj:
            raise _http(404, "Objective not found in session")

    part = None
    if participant_id is not None:
        part = (
            db.query(models.LearningSessionParticipant)
            .filter(
                models.LearningSessionParticipant.id == participant_id,
                models.LearningSessionParticipant.session_id == session_id,
            )
            .first()
        )
        if not part:
            raise _http(404, "Participant not found in session")
        if part.user_id != subject_uid:
            raise _http(422, "participant_id does not match evidence user")
    else:
        part = get_participant_row(db, session_id, user_id=subject_uid)
        if part:
            participant_id = part.id

    # Append-only evidence rows — never overwrite another participant's evidence
    row = models.LearningEvidence(
        session_id=session_id,
        user_id=subject_uid,
        participant_id=participant_id,
        activity_id=activity_id,
        objective_id=objective_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(row)

    # Update participant-level status without changing session lifecycle
    if part and part.role == "STUDENT" and part.status not in ("REMOVED", "LEFT"):
        if event_type == "ACTIVITY_COMPLETED" and part.status in ("INVITED", "JOINED"):
            part.status = "ACTIVE"
            if not part.joined_at:
                part.joined_at = _utcnow()
        if event_type == "ACTIVITY_COMPLETED" and commit:
            db.flush()
            session = get_session(db, session_id)
            progress = compute_participant_progress(db, session, part)
            if progress["progress_status"] == "COMPLETED" and part.status != "COMPLETED":
                part.status = "COMPLETED"

    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def session_to_dict(
    session: models.LearningSession,
    *,
    viewer: Optional[models.User] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    activities = sorted(session.activities or [], key=lambda a: (a.sequence, a.id))
    if viewer is not None and db is not None:
        activities = [a for a in activities if activity_visible_to_user(db, viewer, session, a)]
    return {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "mode": session.mode,
        "status": session.status,
        "course_id": session.course_id,
        "subject_id": session.subject_id,
        "topic_id": session.topic_id,
        "subtopic_id": session.subtopic_id,
        "facilitator_id": session.facilitator_id,
        "created_by": session.created_by,
        "scheduled_start": session.scheduled_start,
        "scheduled_end": session.scheduled_end,
        "actual_start": session.actual_start,
        "actual_end": session.actual_end,
        "outcome_summary": session.outcome_summary,
        "created_at": session.created_at,
        "participants": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "role": p.role,
                "status": p.status,
                "joined_at": p.joined_at,
                "left_at": p.left_at,
            }
            for p in (session.participants or [])
            if p.status != "REMOVED"
        ],
        "objectives": [
            {
                "id": o.id,
                "statement": o.statement,
                "sequence": o.sequence,
                "status": o.status,
                "subject_id": o.subject_id,
                "topic_id": o.topic_id,
                "subtopic_id": o.subtopic_id,
                "concept_tag": o.concept_tag,
            }
            for o in sorted(session.objectives or [], key=lambda x: x.sequence)
        ],
        "activities": [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "title": a.title,
                "description": a.description,
                "sequence": a.sequence,
                "scope": a.scope,
                "participant_id": a.participant_id,
                "status": a.status,
                "assessment_id": a.assessment_id,
                "payload": a.payload,
            }
            for a in activities
        ],
    }
