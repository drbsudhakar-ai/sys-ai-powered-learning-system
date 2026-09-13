"""Phase C bridge between published course workspaces and AI learning sessions.

This service deliberately reuses the P0-013 LearningSession and LearningEvidence
models.  It creates only student-owned *access* to a faculty-owned individual
session; the AI lecturer remains the single teaching engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


OPEN_SESSION_STATUSES = ("DRAFT", "SCHEDULED", "READY", "IN_PROGRESS", "PAUSED")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _published_enrollment(
    db: Session, student: models.User, course_id: int
) -> models.Course:
    if (student.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Student access is required")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    enrolled = (
        db.query(models.StudentCourseEnrollment.id)
        .filter(
            models.StudentCourseEnrollment.student_id == student.id,
            models.StudentCourseEnrollment.course_id == course_id,
            models.StudentCourseEnrollment.status == "ACTIVE",
        )
        .first()
    )
    from app.services.course_enrollments import has_learning_access
    if not enrolled or not course.is_active or course.publication_status not in {"PUBLISHED", "PILOT_PUBLISHED"} or not has_learning_access(db, student.id, course_id):
        raise HTTPException(
            status_code=403,
            detail="Enrollment in this published course is required",
        )
    return course


def _course_topic(db: Session, course_id: int, topic_id: int) -> Tuple[models.Topic, models.Subject]:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Syllabus topic not found")
    subject = db.query(models.Subject).filter(models.Subject.id == topic.subject_id).first()
    if not subject or subject.course_id != course_id:
        raise HTTPException(status_code=422, detail="Topic does not belong to this course")
    return topic, subject


def _facilitator_id(db: Session, course_id: int, subject_id: int) -> int:
    expert = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.subject_id == subject_id)
        .order_by(models.SubjectExpertAssignment.id.asc())
        .first()
    )
    if expert:
        return expert.faculty_id
    coordinator = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.course_id == course_id)
        .order_by(models.FacultyCourseAssignment.id.asc())
        .first()
    )
    if coordinator:
        return coordinator.faculty_id
    raise HTTPException(
        status_code=409,
        detail="A course coordinator or subject expert must be assigned before learning starts",
    )


def _student_topic_sessions(db: Session, student_id: int, course_id: int):
    return (
        db.query(models.LearningSession)
        .join(
            models.LearningSessionParticipant,
            models.LearningSessionParticipant.session_id == models.LearningSession.id,
        )
        .filter(
            models.LearningSessionParticipant.user_id == student_id,
            models.LearningSessionParticipant.role == "STUDENT",
            models.LearningSessionParticipant.status != "REMOVED",
            models.LearningSession.course_id == course_id,
            models.LearningSession.mode == "INDIVIDUAL",
        )
    )


def launch_or_resume_topic(
    db: Session,
    student: models.User,
    *,
    course_id: int,
    topic_id: int,
    subtopic_id: Optional[int] = None,
) -> Dict:
    """Resume one open individual topic session or create it atomically."""
    course = _published_enrollment(db, student, course_id)
    topic, subject = _course_topic(db, course_id, topic_id)
    subtopic = None
    if subtopic_id is not None:
        subtopic = db.query(models.Subtopic).filter(models.Subtopic.id == subtopic_id).first()
        if not subtopic or subtopic.topic_id != topic.id:
            raise HTTPException(status_code=422, detail="Subtopic does not belong to this topic")

    query = _student_topic_sessions(db, student.id, course_id).filter(
        models.LearningSession.topic_id == topic.id,
        models.LearningSession.status.in_(OPEN_SESSION_STATUSES),
    )
    if subtopic_id is None:
        query = query.filter(models.LearningSession.subtopic_id.is_(None))
    else:
        query = query.filter(models.LearningSession.subtopic_id == subtopic_id)
    existing = query.order_by(models.LearningSession.id.desc()).first()
    if existing:
        return _launch_payload(existing, reused=True)

    facilitator_id = _facilitator_id(db, course_id, subject.id)
    now = _utcnow()
    focus = subtopic.name if subtopic else topic.name
    session = models.LearningSession(
        title=f"{focus} — SYS AI Lecturer",
        description=f"Personalized learning for {course.title} · {subject.name} · {focus}",
        mode="INDIVIDUAL",
        status="IN_PROGRESS",
        course_id=course_id,
        subject_id=subject.id,
        topic_id=topic.id,
        subtopic_id=subtopic_id,
        facilitator_id=facilitator_id,
        created_by=facilitator_id,
        actual_start=now,
    )
    db.add(session)
    db.flush()
    db.add_all(
        [
            models.LearningSessionParticipant(
                session_id=session.id,
                user_id=facilitator_id,
                role="FACILITATOR",
                status="JOINED",
                joined_at=now,
            ),
            models.LearningSessionParticipant(
                session_id=session.id,
                user_id=student.id,
                role="STUDENT",
                status="ACTIVE",
                joined_at=now,
            ),
            models.LearningSessionObjective(
                session_id=session.id,
                statement=f"Understand and apply {focus}",
                sequence=1,
                subject_id=subject.id,
                topic_id=topic.id,
                subtopic_id=subtopic_id,
                concept_tag=focus,
            ),
            models.LearningEvidence(
                session_id=session.id,
                user_id=student.id,
                event_type="SESSION_STARTED",
                payload={"source": "course_workspace", "topic_id": topic.id},
            ),
        ]
    )
    db.commit()
    db.refresh(session)
    return _launch_payload(session, reused=False)


def _launch_payload(session: models.LearningSession, *, reused: bool) -> Dict:
    return {
        "session_id": session.id,
        "course_id": session.course_id,
        "subject_id": session.subject_id,
        "topic_id": session.topic_id,
        "subtopic_id": session.subtopic_id,
        "mode": session.mode,
        "status": session.status,
        "reused": reused,
        "classroom_path": f"/learning-sessions/{session.id}/lecture?course_id={session.course_id}",
        "message": "Existing AI lesson resumed." if reused else "AI lesson created successfully.",
    }


def student_learning_summary(db: Session, student_id: int, course_id: int) -> Dict:
    from app.services.learning_workspace import summary
    return summary(db, student_id, course_id)
