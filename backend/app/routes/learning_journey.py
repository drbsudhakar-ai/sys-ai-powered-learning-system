"""P0-017 Personalized Learning Journey APIs."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.routes.auth import get_current_user
from app.services import learning_orchestrator as orch

router = APIRouter(prefix="/learning-journey", tags=["Learning Journey"])


@router.get("/me")
def my_journey(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.build_journey(
        db, current_user, student_id=current_user.id, course_id=course_id
    )


@router.get("/me/next")
def my_next(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = orch.build_journey(
        db, current_user, student_id=current_user.id, course_id=course_id
    )
    return {
        "course_id": course_id,
        "next_best_action": data["next_best_action"],
        "alternatives": data["alternatives"],
        "resume": data["resume"],
        "explanation": (data.get("next_best_action") or {}).get("explanation"),
    }


@router.get("/me/actions")
def my_actions(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.list_my_actions(db, current_user, course_id=course_id)


@router.get("/me/progress")
def my_progress(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.progress_view(
        db, current_user, student_id=current_user.id, course_id=course_id
    )


@router.post("/me/actions/{action_id}/start")
def start_action(
    action_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.start_action(db, current_user, action_id)


@router.post("/me/actions/{action_id}/complete")
def complete_action(
    action_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.complete_action(db, current_user, action_id)


@router.post("/me/actions/{action_id}/dismiss")
def dismiss_action(
    action_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.dismiss_action(db, current_user, action_id)


@router.post("/me/actions/{action_id}/choose")
def choose_action(
    action_id: int,
    payload: schemas.LearningActionChoose,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.choose_action(
        db, current_user, action_id, choice_action_id=payload.choice_action_id
    )


@router.get("/faculty/students")
def faculty_students(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.faculty_students(db, current_user, course_id=course_id)


@router.get("/faculty/students/{student_id}")
def faculty_student(
    student_id: int,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.faculty_student(
        db, current_user, student_id=student_id, course_id=course_id
    )


@router.post("/faculty/students/{student_id}/recommend")
def faculty_recommend(
    student_id: int,
    payload: schemas.FacultyJourneyRecommend,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.faculty_recommend(
        db,
        current_user,
        student_id=student_id,
        course_id=payload.course_id,
        action_type=payload.action_type,
        topic_id=payload.topic_id,
        reason=payload.reason,
    )


@router.get("/admin/overview")
def admin_overview(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return orch.admin_overview(db, current_user, course_id=course_id)
