"""P0-016 Learning Intelligence & Early-Warning Analytics APIs."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, database
from app.routes.auth import get_current_user
from app.services import early_warning as ew
from app.services import learning_analytics as la

router = APIRouter(prefix="/analytics", tags=["Learning Intelligence"])


@router.get("/policy")
def get_analytics_policy(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ew.get_warning_policy(db, course_id)


@router.get("/me")
def my_analytics(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.student_analytics(
        db, current_user, student_id=current_user.id, course_id=course_id
    )


@router.get("/me/topics")
def my_topics(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = la.student_analytics(
        db, current_user, student_id=current_user.id, course_id=course_id
    )
    return {
        "course_id": course_id,
        "topics": data["topics"],
        "mastered_topics": data["mastered_topics"],
        "improving_topics": data["improving_topics"],
        "needs_practice": data["needs_practice"],
        "needs_support": data["needs_support"],
    }


@router.get("/me/trends")
def my_trends(
    course_id: int = Query(...),
    topic_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.student_trends(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        topic_id=topic_id,
    )


@router.get("/me/attention")
def my_attention(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = la.student_analytics(
        db, current_user, student_id=current_user.id, course_id=course_id
    )
    return {
        "course_id": course_id,
        "attention": data["attention"],
        "recommendations": data["recommendations"],
    }


@router.get("/students/{student_id}/courses/{course_id}")
def student_analytics(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.student_analytics(
        db, current_user, student_id=student_id, course_id=course_id
    )


@router.get("/faculty/overview")
def faculty_overview(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.faculty_overview(db, current_user, course_id=course_id)


@router.get("/faculty/topics")
def faculty_topics(
    course_id: int = Query(...),
    subject_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.faculty_topics(
        db, current_user, course_id=course_id, subject_id=subject_id
    )


@router.get("/faculty/students")
def faculty_students(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Lightweight student roster with mastery summary counts (no peer detail dump)."""
    la._authorize_faculty_course(db, current_user, course_id)
    enrollments = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.course_id == course_id)
        .all()
    )
    rows = []
    for enr in enrollments:
        states = (
            db.query(models.TopicMasteryState)
            .filter(
                models.TopicMasteryState.student_id == enr.student_id,
                models.TopicMasteryState.course_id == course_id,
            )
            .all()
        )
        user = db.query(models.User).filter(models.User.id == enr.student_id).first()
        from collections import Counter

        dist = Counter(s.status for s in states)
        rows.append(
            {
                "student_id": enr.student_id,
                "student_name": user.name if user else None,
                "mastery_distribution": dict(dist),
                "mastered": dist.get("MASTERED", 0),
                "needs_support": dist.get("NEEDS_REMEDIATION", 0)
                + dist.get("MASTERY_REGRESSED", 0),
            }
        )
    return {"course_id": course_id, "students": rows}


@router.get("/faculty/attention")
def faculty_attention(
    course_id: int = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.faculty_attention(db, current_user, course_id=course_id, limit=limit)


@router.get("/faculty/interventions")
def faculty_interventions(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.faculty_interventions(db, current_user, course_id=course_id)


@router.post("/faculty/attention/notify")
def faculty_attention_notify(
    course_id: int = Query(...),
    student_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.emit_attention_notifications(
        db, current_user, course_id=course_id, student_id=student_id
    )


@router.get("/admin/overview")
def admin_overview(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.admin_overview(db, current_user, course_id=course_id)


@router.get("/admin/courses")
def admin_courses(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.admin_courses(db, current_user)


@router.get("/admin/subjects")
def admin_subjects(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.admin_subjects(db, current_user, course_id=course_id)


@router.get("/admin/trends")
def admin_trends(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mastery transition counts from append-only events (no fabricated history)."""
    la._authorize_admin(current_user)
    q = db.query(models.MasteryEvent)
    if course_id is not None:
        q = q.filter(models.MasteryEvent.course_id == course_id)
    events = q.order_by(models.MasteryEvent.created_at.desc()).limit(500).all()
    from collections import Counter

    by_type = Counter(e.event_type for e in events)
    return {
        "course_id": course_id,
        "event_counts": dict(by_type),
        "recent": [
            {
                "event_type": e.event_type,
                "course_id": e.course_id,
                "topic_id": e.topic_id,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events[:50]
        ],
    }


@router.get("/admin/attention")
def admin_attention(
    course_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return la.admin_attention(db, current_user, course_id=course_id, limit=limit)
