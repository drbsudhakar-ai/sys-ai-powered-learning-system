"""Topics, Subtopics, Questions — Assessment boundary (P0-009)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.academic_auth import require_assessment_designer, is_admin, require_question_author
from app.constants import DIFFICULTIES
from app.routes.auth import get_current_user, require_roles
from app.services.similarity import fingerprint

router = APIRouter(tags=["Curriculum"])
_staff = require_roles("admin", "faculty")


@router.get("/topics", response_model=List[schemas.TopicOut])
def list_topics(
    subject_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.Topic)
    if subject_id is not None:
        q = q.filter(models.Topic.subject_id == subject_id)
    return q.order_by(models.Topic.name).all()


@router.post("/topics", response_model=schemas.TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: schemas.TopicCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if subject.course_id:
        require_assessment_designer(db, current_user, subject.course_id)
    elif not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    topic = models.Topic(name=payload.name, description=payload.description, subject_id=payload.subject_id)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.get("/subtopics", response_model=List[schemas.SubtopicOut])
def list_subtopics(
    topic_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.Subtopic)
    if topic_id is not None:
        q = q.filter(models.Subtopic.topic_id == topic_id)
    return q.order_by(models.Subtopic.name).all()


@router.post("/subtopics", response_model=schemas.SubtopicOut, status_code=status.HTTP_201_CREATED)
def create_subtopic(
    payload: schemas.SubtopicCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    topic = db.query(models.Topic).filter(models.Topic.id == payload.topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    subject = db.query(models.Subject).filter(models.Subject.id == topic.subject_id).first()
    if subject and subject.course_id:
        require_assessment_designer(db, current_user, subject.course_id)
    elif not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    row = models.Subtopic(name=payload.name, description=payload.description, topic_id=payload.topic_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/questions", response_model=List[schemas.QuestionOut])
def list_questions(
    course_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    topic_id: Optional[int] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    q = db.query(models.Question)
    if course_id is not None:
        require_assessment_designer(db, current_user, course_id)
        q = q.filter(models.Question.course_id == course_id)
    if subject_id is not None:
        q = q.filter(models.Question.subject_id == subject_id)
    if topic_id is not None:
        q = q.filter(models.Question.topic_id == topic_id)
    if difficulty is not None:
        q = q.filter(models.Question.difficulty == difficulty)
    return q.order_by(models.Question.id.desc()).limit(500).all()


@router.post("/questions", response_model=schemas.QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: schemas.QuestionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_question_author(db, current_user, payload.course_id, payload.subject_id)
    if payload.difficulty not in DIFFICULTIES:
        raise HTTPException(status_code=422, detail="Invalid difficulty")
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if subject.course_id and subject.course_id != payload.course_id:
        raise HTTPException(status_code=422, detail="Subject does not belong to course")
    if payload.topic_id:
        topic = db.query(models.Topic).filter(models.Topic.id == payload.topic_id).first()
        if not topic or topic.subject_id != payload.subject_id:
            raise HTTPException(status_code=422, detail="Topic does not belong to subject")
    q = models.Question(
        stem=payload.stem,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        status=payload.status or "ACTIVE",
        course_id=payload.course_id,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        subtopic_id=payload.subtopic_id,
        created_by=current_user.id,
        similarity_fingerprint=fingerprint(payload.stem),
        novelty_class="NOVEL",
        marks=1.0,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q
