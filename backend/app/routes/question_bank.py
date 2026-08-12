"""Question Bank CRUD + search (P0-010). Extends P0-009 question boundary."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.academic_auth import require_question_author, can_access_course_questions, is_admin
from app.constants import DIFFICULTIES, QUESTION_STATUSES, QUESTION_TYPES
from app.routes.auth import get_current_user, require_roles
from app.services.similarity import fingerprint, find_duplicates

router = APIRouter(prefix="/question-bank", tags=["Question Bank"])
_staff = require_roles("admin", "faculty")


def _validate_question_payload(db: Session, payload, *, for_update: bool = False):
    qtype = getattr(payload, "question_type", None) or "SINGLE_MCQ"
    if qtype not in QUESTION_TYPES:
        raise HTTPException(status_code=422, detail="Invalid question_type")
    difficulty = getattr(payload, "difficulty", None) or "MEDIUM"
    if difficulty not in DIFFICULTIES:
        raise HTTPException(status_code=422, detail="Invalid difficulty")
    status_v = getattr(payload, "status", None)
    if status_v and status_v not in QUESTION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    stem = getattr(payload, "stem", None) or getattr(payload, "question_text", None)
    if stem is not None and not str(stem).strip():
        raise HTTPException(status_code=422, detail="Question text is required")

    options = getattr(payload, "options", None)
    if options is not None:
        if not isinstance(options, list):
            raise HTTPException(status_code=422, detail="options must be a list")
        cleaned = [str(o).strip() for o in options if str(o).strip()]
        if len(cleaned) != len(set(o.lower() for o in cleaned)):
            raise HTTPException(status_code=422, detail="Duplicate options are not allowed")

    correct = getattr(payload, "correct_answer", None)
    if status_v in ("APPROVED", "ACTIVE") and not correct:
        raise HTTPException(status_code=422, detail="correct_answer required for APPROVED/ACTIVE questions")

    marks = getattr(payload, "marks", None)
    if marks is not None and marks < 0:
        raise HTTPException(status_code=422, detail="marks cannot be negative")

    course_id = getattr(payload, "course_id", None)
    subject_id = getattr(payload, "subject_id", None)
    if course_id and subject_id:
        subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        if subject.course_id and subject.course_id != course_id:
            raise HTTPException(status_code=422, detail="Subject does not belong to course")
        topic_id = getattr(payload, "topic_id", None)
        if topic_id:
            topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
            if not topic or topic.subject_id != subject_id:
                raise HTTPException(status_code=422, detail="Topic does not belong to subject")


def _to_out(q: models.Question) -> schemas.QuestionBankOut:
    return schemas.QuestionBankOut(
        id=q.id,
        stem=q.stem,
        question_text=q.stem,
        question_type=q.question_type,
        difficulty=q.difficulty,
        status=q.status,
        course_id=q.course_id,
        subject_id=q.subject_id,
        topic_id=q.topic_id,
        subtopic_id=q.subtopic_id,
        options=q.options,
        correct_answer=q.correct_answer,
        explanation=q.explanation,
        marks=q.marks,
        negative_marks=q.negative_marks,
        source=q.source,
        source_year=q.source_year,
        exam_name=q.exam_name,
        concept_tags=q.concept_tags,
        learning_objective=q.learning_objective,
        shortcut=q.shortcut,
        alternative_solution=q.alternative_solution,
        common_traps=q.common_traps,
        estimated_time_seconds=q.estimated_time_seconds,
        quality_score=q.quality_score,
        novelty_class=q.novelty_class,
        created_by=q.created_by,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


@router.get("/questions", response_model=List[schemas.QuestionBankOut])
def search_questions(
    course_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    topic_id: Optional[int] = Query(None),
    difficulty: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    question_type: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    query = db.query(models.Question)
    if course_id is not None:
        if not can_access_course_questions(db, current_user, course_id) and not is_admin(current_user):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        query = query.filter(models.Question.course_id == course_id)
    if subject_id is not None:
        query = query.filter(models.Question.subject_id == subject_id)
    if topic_id is not None:
        query = query.filter(models.Question.topic_id == topic_id)
    if difficulty:
        query = query.filter(models.Question.difficulty == difficulty)
    if status_filter:
        query = query.filter(models.Question.status == status_filter)
    if question_type:
        query = query.filter(models.Question.question_type == question_type)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Question.stem.ilike(like))
    rows = query.order_by(models.Question.id.desc()).offset(skip).limit(limit).all()
    return [_to_out(r) for r in rows]


@router.get("/questions/{question_id}", response_model=schemas.QuestionBankOut)
def get_question(
    question_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    row = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    if not can_access_course_questions(db, current_user, row.course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return _to_out(row)


@router.post("/questions", response_model=schemas.QuestionBankOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: schemas.QuestionBankCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_question_author(db, current_user, payload.course_id, payload.subject_id)
    _validate_question_payload(db, payload)
    stem = payload.stem or payload.question_text
    existing = (
        db.query(models.Question.id, models.Question.stem)
        .filter(models.Question.course_id == payload.course_id)
        .all()
    )
    dups = find_duplicates(stem, [(r.id, r.stem) for r in existing])
    if dups and dups[0]["class"] == "EXACT_PREVIOUS":
        raise HTTPException(
            status_code=409,
            detail={"message": "Exact duplicate question exists", "matches": dups[:5]},
        )

    row = models.Question(
        stem=stem.strip(),
        question_type=payload.question_type or "SINGLE_MCQ",
        difficulty=payload.difficulty,
        status=payload.status or "DRAFT",
        course_id=payload.course_id,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        subtopic_id=payload.subtopic_id,
        options=payload.options,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        marks=payload.marks if payload.marks is not None else 1.0,
        negative_marks=payload.negative_marks if payload.negative_marks is not None else 0.0,
        source=payload.source,
        source_year=payload.source_year,
        exam_name=payload.exam_name,
        concept_tags=payload.concept_tags,
        learning_objective=payload.learning_objective,
        shortcut=payload.shortcut,
        alternative_solution=payload.alternative_solution,
        common_traps=payload.common_traps,
        estimated_time_seconds=payload.estimated_time_seconds,
        quality_score=payload.quality_score,
        novelty_class=payload.novelty_class or "NOVEL",
        similarity_fingerprint=fingerprint(stem),
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.put("/questions/{question_id}", response_model=schemas.QuestionBankOut)
def update_question(
    question_id: int,
    payload: schemas.QuestionBankUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    row = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    require_question_author(db, current_user, row.course_id, row.subject_id)
    data = payload.model_dump(exclude_unset=True)
    if "question_text" in data and "stem" not in data:
        data["stem"] = data.pop("question_text")
    elif "question_text" in data:
        data.pop("question_text")
    # build temp object-like for validation
    class _Tmp:
        pass
    tmp = _Tmp()
    for k in [
        "stem", "question_type", "difficulty", "status", "options", "correct_answer",
        "marks", "course_id", "subject_id", "topic_id",
    ]:
        setattr(tmp, k, data.get(k, getattr(row, k if k != "stem" else "stem", None)))
    tmp.course_id = row.course_id
    tmp.subject_id = data.get("subject_id", row.subject_id)
    tmp.topic_id = data.get("topic_id", row.topic_id)
    _validate_question_payload(db, tmp, for_update=True)
    for k, v in data.items():
        setattr(row, k, v)
    if "stem" in data:
        row.similarity_fingerprint = fingerprint(row.stem)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/questions/{question_id}/duplicate", response_model=schemas.QuestionBankOut, status_code=201)
def duplicate_question(
    question_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    src = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Question not found")
    require_question_author(db, current_user, src.course_id, src.subject_id)
    copy = models.Question(
        stem=f"[Copy] {src.stem}",
        question_type=src.question_type,
        difficulty=src.difficulty,
        status="DRAFT",
        course_id=src.course_id,
        subject_id=src.subject_id,
        topic_id=src.topic_id,
        subtopic_id=src.subtopic_id,
        options=src.options,
        correct_answer=src.correct_answer,
        explanation=src.explanation,
        marks=src.marks,
        negative_marks=src.negative_marks,
        source=src.source,
        source_year=src.source_year,
        exam_name=src.exam_name,
        concept_tags=src.concept_tags,
        learning_objective=src.learning_objective,
        shortcut=src.shortcut,
        alternative_solution=src.alternative_solution,
        common_traps=src.common_traps,
        estimated_time_seconds=src.estimated_time_seconds,
        quality_score=src.quality_score,
        novelty_class="NOVEL",
        similarity_fingerprint=fingerprint(f"[Copy] {src.stem}"),
        created_by=current_user.id,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _to_out(copy)


@router.post("/questions/{question_id}/archive", response_model=schemas.QuestionBankOut)
def archive_question(
    question_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    row = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    require_question_author(db, current_user, row.course_id, row.subject_id)
    row.status = "ARCHIVED"
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/questions/check-similarity")
def check_similarity(
    payload: schemas.SimilarityCheckIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    if not can_access_course_questions(db, current_user, payload.course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    existing = (
        db.query(models.Question.id, models.Question.stem)
        .filter(models.Question.course_id == payload.course_id)
        .all()
    )
    return {"matches": find_duplicates(payload.text, [(r.id, r.stem) for r in existing])}
