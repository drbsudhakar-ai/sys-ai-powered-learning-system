"""P0-017 Personalized Learning Journey APIs."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.routes.auth import get_current_user
from app.services import learning_orchestrator as orch
from app.services import subject_progression as sp

router = APIRouter(prefix="/learning-journey", tags=["Learning Journey"])


@router.get("/me")
def my_journey(
    course_id: int = Query(...),
    subject_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = orch.build_journey(
        db, current_user, student_id=current_user.id, course_id=course_id
    )
    subjects = sp.list_course_subjects(
        db, current_user, student_id=current_user.id, course_id=course_id
    )
    data["subjects"] = subjects["subjects"]
    data["subject_order_imposed"] = False
    sid = subject_id or sp.last_focused_subject_id(
        db, student_id=current_user.id, course_id=course_id
    )
    if sid:
        data["subject_guidance"] = sp.subject_view(
            db,
            current_user,
            student_id=current_user.id,
            course_id=course_id,
            subject_id=sid,
            notify=True,
        )
    else:
        bal = sp.evaluate_course_balance(
            db, student_id=current_user.id, course_id=course_id
        )
        sp.maybe_notify_imbalance(
            db, student_id=current_user.id, course_id=course_id, balance=bal
        )
        data["course_balance"] = {
            "status": bal["balance_status"],
            "reason": bal["reason"],
            "subjects": bal["subjects"],
            "lagging_subject": bal.get("lagging_subject"),
            "does_not_force_subject_switch": True,
        }
        data["subject_guidance"] = None
    return data


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
    data = orch.faculty_students(db, current_user, course_id=course_id)
    for row in data.get("students") or []:
        bal = sp.evaluate_course_balance(
            db, student_id=row["student_id"], course_id=course_id
        )
        row["balance_status"] = bal["balance_status"]
        lag = bal.get("lagging_subject") or {}
        row["lagging_subject"] = lag.get("subject_name")
        row["balance_reason"] = bal.get("reason")
    return data


@router.get("/faculty/students/{student_id}")
def faculty_student(
    student_id: int,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = orch.faculty_student(
        db, current_user, student_id=student_id, course_id=course_id
    )
    data["subjects"] = sp.list_course_subjects(
        db, current_user, student_id=student_id, course_id=course_id
    )["subjects"]
    data["subject_order_imposed"] = False
    data["course_balance"] = sp.evaluate_course_balance(
        db, student_id=student_id, course_id=course_id
    )
    return data


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


@router.get("/me/subjects")
def my_subjects(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return sp.list_course_subjects(
        db, current_user, student_id=current_user.id, course_id=course_id
    )


@router.get("/me/subjects/{subject_id}")
def my_subject(
    subject_id: int,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return sp.subject_view(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        subject_id=subject_id,
        notify=True,
    )


@router.get("/me/subjects/{subject_id}/next")
def my_subject_next(
    subject_id: int,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    sp.focus_subject(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        subject_id=subject_id,
    )
    rec = sp.recommend_topic_in_subject(
        db, student_id=current_user.id, course_id=course_id, subject_id=subject_id
    )
    return rec


@router.post("/me/subjects/{subject_id}/focus")
def focus_my_subject(
    subject_id: int,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    sp.focus_subject(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        subject_id=subject_id,
    )
    return sp.subject_view(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        subject_id=subject_id,
        notify=False,
    )


@router.post("/me/subjects/{subject_id}/topics/choose")
def choose_subject_topic(
    subject_id: int,
    payload: schemas.SubjectTopicChoose,
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return sp.choose_topic(
        db,
        current_user,
        student_id=current_user.id,
        course_id=course_id,
        subject_id=subject_id,
        topic_id=payload.topic_id,
    )
