"""Academic authorization helpers (reuses P0-004/P0-008 structures)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models


def is_admin(user: models.User) -> bool:
    return (user.role or "").lower() == "admin"


def is_course_coordinator(db: Session, user: models.User, course_id: int) -> bool:
    if (user.role or "").lower() != "faculty":
        return False
    row = (
        db.query(models.FacultyCourseAssignment)
        .filter(
            models.FacultyCourseAssignment.faculty_id == user.id,
            models.FacultyCourseAssignment.course_id == course_id,
        )
        .first()
    )
    return row is not None


def is_subject_expert(db: Session, user: models.User, subject_id: int) -> bool:
    if (user.role or "").lower() != "faculty":
        return False
    row = (
        db.query(models.SubjectExpertAssignment)
        .filter(
            models.SubjectExpertAssignment.faculty_id == user.id,
            models.SubjectExpertAssignment.subject_id == subject_id,
        )
        .first()
    )
    return row is not None


def require_assessment_designer(db: Session, user: models.User, course_id: int) -> None:
    """Admin or Course Coordinator for the course may design assessments."""
    if is_admin(user):
        return
    if is_course_coordinator(db, user, course_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for this course",
    )


def require_course_report_access(db: Session, user: models.User, course_id: int) -> None:
    """Admin or Course Coordinator may view performance/reports for a course."""
    require_assessment_designer(db, user, course_id)


def get_coordinated_course_ids(db: Session, user: models.User) -> list[int]:
    if is_admin(user):
        return [c.id for c in db.query(models.Course).all()]
    rows = (
        db.query(models.FacultyCourseAssignment.course_id)
        .filter(models.FacultyCourseAssignment.faculty_id == user.id)
        .all()
    )
    return [r[0] for r in rows]
