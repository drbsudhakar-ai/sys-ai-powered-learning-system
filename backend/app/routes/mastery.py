"""P0-015 Adaptive Practice & Mastery APIs."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.routes.auth import get_current_user
from app.services import mastery_engine as mastery

router = APIRouter(prefix="/mastery", tags=["Adaptive Practice & Mastery"])


@router.get("/policy")
def get_policy(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return mastery.get_policy(db, course_id)


@router.put("/policy")
def put_policy(
    payload: schemas.MasteryPolicyUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    course_id = data.pop("course_id", None)
    return mastery.upsert_policy(db, current_user, course_id=course_id, **data)


@router.get("/students/{student_id}/courses/{course_id}")
def list_student_mastery(
    student_id: int,
    course_id: int,
    sync: bool = Query(True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return mastery.list_mastery(
        db, current_user, student_id=student_id, course_id=course_id, sync=sync
    )


@router.get("/students/{student_id}/courses/{course_id}/topics/{topic_id}")
def get_topic_mastery(
    student_id: int,
    course_id: int,
    topic_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return mastery.get_topic_mastery(
        db,
        current_user,
        student_id=student_id,
        course_id=course_id,
        topic_id=topic_id,
    )


@router.get("/me")
def my_mastery(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return mastery.list_mastery(
        db, current_user, student_id=current_user.id, course_id=course_id, sync=True
    )


@router.post("/practice/recommend")
def recommend_practice(
    payload: schemas.MasteryTopicAction,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    student_id = payload.student_id or current_user.id
    return mastery.recommend_practice(
        db,
        current_user,
        student_id=student_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
    )


@router.post("/practice/start")
def start_practice(
    payload: schemas.MasteryTopicAction,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    student_id = payload.student_id or current_user.id
    return mastery.start_practice(
        db,
        current_user,
        student_id=student_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
    )


@router.get("/reassessment/eligibility")
def reassessment_eligibility(
    course_id: int = Query(...),
    topic_id: int = Query(...),
    student_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    sid = student_id or current_user.id
    return mastery.check_reassessment_eligibility(
        db, current_user, student_id=sid, course_id=course_id, topic_id=topic_id
    )


@router.post("/reassessment/declare-ready")
def declare_ready(
    payload: schemas.MasteryDeclareReady,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    student_id = payload.student_id or current_user.id
    return mastery.declare_ready(
        db,
        current_user,
        student_id=student_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
        remediation_source=payload.remediation_source or "SELF_STUDY",
    )


@router.post("/reassessment/approve")
def approve_reassessment(
    payload: schemas.MasteryTopicAction,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not payload.student_id:
        raise HTTPException(status_code=422, detail="student_id required for faculty approval")
    return mastery.faculty_approve_reassessment(
        db,
        current_user,
        student_id=payload.student_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
    )


@router.post("/reassessment/start")
def start_reassessment(
    payload: schemas.MasteryTopicAction,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    student_id = payload.student_id or current_user.id
    return mastery.start_reassessment(
        db,
        current_user,
        student_id=student_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
    )
