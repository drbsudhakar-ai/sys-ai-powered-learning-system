"""
Assessment Engine routes (P0-009)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app import models, schemas, database
from app.academic_auth import require_assessment_designer, is_admin, get_coordinated_course_ids
from app.constants import ASSESSMENT_STATUSES, DIFFICULTIES, MULTI_SUBJECT_TYPES
from app.routes.auth import get_current_user, require_roles
from app.services import assessment_engine as engine
from app.services import notifications as notif_svc

router = APIRouter(prefix="/assessments", tags=["Assessments"])
_staff = require_roles("admin", "faculty")


def _assessment_out(a: models.Assessment) -> schemas.AssessmentOut:
    versions = []
    for v in a.versions or []:
        versions.append(
            schemas.AssessmentVersionOut(
                id=v.id,
                assessment_id=v.assessment_id,
                version_number=v.version_number,
                duration_minutes=v.duration_minutes,
                total_questions=v.total_questions,
                total_marks=v.total_marks,
                category=v.category,
                assessment_type=v.assessment_type,
                published_at=v.published_at,
                questions=[
                    schemas.AssessmentQuestionOut.model_validate(q) for q in (v.questions or [])
                ],
            )
        )
    return schemas.AssessmentOut(
        id=a.id,
        title=a.title,
        course_id=a.course_id,
        created_at=a.created_at,
        due_date=a.due_date,
        created_by=a.created_by,
        category=a.category,
        assessment_type=a.assessment_type,
        status=a.status or "DRAFT",
        duration_minutes=a.duration_minutes,
        total_questions=a.total_questions,
        total_marks=a.total_marks,
        marks_correct=a.marks_correct,
        marks_incorrect=a.marks_incorrect,
        marks_unanswered=a.marks_unanswered,
        subject_id=a.subject_id,
        topic_id=a.topic_id,
        blueprint_items=[schemas.BlueprintItemOut.model_validate(i) for i in (a.blueprint_items or [])],
        versions=versions,
    )


def _load_assessment(db: Session, assessment_id: int) -> models.Assessment:
    a = (
        db.query(models.Assessment)
        .options(
            joinedload(models.Assessment.blueprint_items),
            joinedload(models.Assessment.versions).joinedload(models.AssessmentVersion.questions),
        )
        .filter(models.Assessment.id == assessment_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a


@router.post("/", response_model=schemas.AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: schemas.AssessmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    course = db.query(models.Course).filter(models.Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    require_assessment_designer(db, current_user, payload.course_id)

    category = engine.validate_type_category(payload.assessment_type, payload.category)
    engine.validate_marking(
        payload.marks_correct,
        payload.marks_incorrect,
        payload.marks_unanswered,
        payload.duration_minutes,
        payload.total_questions,
        payload.total_marks,
    )

    if payload.assessment_type in ("TOPIC_TEST", "ADAPTIVE_PRACTICE", "TOPIC_REASSESSMENT"):
        if not payload.subject_id or not payload.topic_id:
            raise HTTPException(
                status_code=422,
                detail="Topic-scoped assessments require subject_id and topic_id",
            )
        topic = db.query(models.Topic).filter(models.Topic.id == payload.topic_id).first()
        if not topic or topic.subject_id != payload.subject_id:
            raise HTTPException(status_code=422, detail="Topic does not belong to subject")

    if payload.subject_id:
        subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        if subject.course_id and subject.course_id != payload.course_id:
            raise HTTPException(status_code=422, detail="Subject does not belong to course")

    a = models.Assessment(
        title=payload.title,
        course_id=payload.course_id,
        due_date=payload.due_date,
        created_by=current_user.id,
        category=category,
        assessment_type=payload.assessment_type,
        status="DRAFT",
        duration_minutes=payload.duration_minutes,
        total_questions=payload.total_questions,
        total_marks=payload.total_marks,
        marks_correct=payload.marks_correct if payload.marks_correct is not None else 1.0,
        marks_incorrect=payload.marks_incorrect if payload.marks_incorrect is not None else 0.0,
        marks_unanswered=payload.marks_unanswered if payload.marks_unanswered is not None else 0.0,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        available_from=payload.available_from,
        available_until=payload.available_until,
        max_attempts=payload.max_attempts if payload.max_attempts is not None else 1,
    )
    db.add(a)
    db.commit()
    return _assessment_out(_load_assessment(db, a.id))


@router.get("/", response_model=List[schemas.AssessmentOut])
def list_assessments(
    course_id: Optional[int] = Query(None),
    assessment_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Assessment)
    role = (current_user.role or "").lower()
    if role == "student":
        # Students may list published assessments only
        q = q.filter(models.Assessment.status == "PUBLISHED")
    elif role == "faculty" and not is_admin(current_user):
        allowed = get_coordinated_course_ids(db, current_user)
        q = q.filter(models.Assessment.course_id.in_(allowed or [-1]))

    if course_id is not None:
        q = q.filter(models.Assessment.course_id == course_id)
    if assessment_type:
        q = q.filter(models.Assessment.assessment_type == assessment_type)
    if category:
        q = q.filter(models.Assessment.category == category)
    if status_filter:
        q = q.filter(models.Assessment.status == status_filter)

    rows = q.order_by(models.Assessment.id.desc()).all()
    return [_assessment_out(_load_assessment(db, r.id)) for r in rows]


@router.get("/{assessment_id}", response_model=schemas.AssessmentOut)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    a = _load_assessment(db, assessment_id)
    role = (current_user.role or "").lower()
    if role == "student" and a.status != "PUBLISHED":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if role == "faculty" and not is_admin(current_user):
        require_assessment_designer(db, current_user, a.course_id)
    return _assessment_out(a)


@router.put("/{assessment_id}", response_model=schemas.AssessmentOut)
def update_assessment(
    assessment_id: int,
    payload: schemas.AssessmentUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)
    if a.status == "PUBLISHED" and payload.status != "ARCHIVED":
        # Allow limited metadata updates but prefer new version for major changes
        pass
    if a.status == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Cannot edit archived assessment")

    data = payload.model_dump(exclude_unset=True)
    if "assessment_type" in data or "category" in data:
        a_type = data.get("assessment_type", a.assessment_type)
        cat = data.get("category", a.category)
        data["category"] = engine.validate_type_category(a_type, cat)
    engine.validate_marking(
        data.get("marks_correct", a.marks_correct),
        data.get("marks_incorrect", a.marks_incorrect),
        data.get("marks_unanswered", a.marks_unanswered),
        data.get("duration_minutes", a.duration_minutes),
        data.get("total_questions", a.total_questions),
        data.get("total_marks", a.total_marks),
    )
    if "status" in data and data["status"] not in ASSESSMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    # course_id changes not supported via update schema
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    return _assessment_out(_load_assessment(db, a.id))


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_or_delete_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)
    if a.status == "PUBLISHED" or a.versions:
        a.status = "ARCHIVED"
        db.commit()
        return None
    db.delete(a)
    db.commit()
    return None


@router.put("/{assessment_id}/blueprint", response_model=schemas.AssessmentOut)
def set_blueprint(
    assessment_id: int,
    items: List[schemas.BlueprintItemIn],
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)
    if a.status == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Cannot edit archived assessment")

    for item in items:
        if item.difficulty not in DIFFICULTIES:
            raise HTTPException(status_code=422, detail=f"Invalid difficulty: {item.difficulty}")

    # Replace blueprint (draft may be incomplete; publish enforces full validation)
    db.query(models.AssessmentBlueprintItem).filter(
        models.AssessmentBlueprintItem.assessment_id == assessment_id
    ).delete()
    for item in items:
        db.add(
            models.AssessmentBlueprintItem(
                assessment_id=assessment_id,
                subject_id=item.subject_id,
                topic_id=item.topic_id,
                subtopic_id=item.subtopic_id,
                difficulty=item.difficulty,
                question_count=item.question_count,
            )
        )
    db.commit()
    return _assessment_out(_load_assessment(db, assessment_id))


@router.post("/{assessment_id}/assemble", response_model=dict)
def assemble_preview(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)
    selected, errors = engine.assemble_questions(db, a, list(a.blueprint_items))
    return {
        "ok": not errors,
        "errors": errors,
        "selected_question_ids": [q.id for q in selected],
        "count": len(selected),
    }


@router.post("/{assessment_id}/publish", response_model=schemas.PublishResult)
def publish_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)

    if not a.duration_minutes or a.duration_minutes <= 0:
        raise HTTPException(status_code=422, detail="Valid duration_minutes required before publish")
    if not a.total_questions or a.total_questions <= 0:
        raise HTTPException(status_code=422, detail="total_questions required before publish")
    if not a.total_marks or a.total_marks <= 0:
        raise HTTPException(status_code=422, detail="total_marks required before publish")
    if not a.assessment_type:
        raise HTTPException(status_code=422, detail="assessment_type required")

    selected, errors = engine.assemble_questions(db, a, list(a.blueprint_items))
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    next_ver = (max((v.version_number for v in a.versions), default=0) + 1)
    blueprint_snap = [
        {
            "subject_id": i.subject_id,
            "topic_id": i.topic_id,
            "subtopic_id": i.subtopic_id,
            "difficulty": i.difficulty,
            "question_count": i.question_count,
        }
        for i in a.blueprint_items
    ]
    marking_snap = {
        "marks_correct": a.marks_correct,
        "marks_incorrect": a.marks_incorrect,
        "marks_unanswered": a.marks_unanswered,
    }
    version = models.AssessmentVersion(
        assessment_id=a.id,
        version_number=next_ver,
        blueprint_snapshot=blueprint_snap,
        marking_snapshot=marking_snap,
        duration_minutes=a.duration_minutes,
        total_questions=a.total_questions,
        total_marks=a.total_marks,
        category=a.category,
        assessment_type=a.assessment_type,
        published_by=current_user.id,
    )
    db.add(version)
    db.flush()

    from app.services.attempt_engine import snapshot_question_onto_aq

    marks_each = float(a.marks_correct or 1.0)
    neg = float(a.marks_incorrect or 0.0)
    for idx, q in enumerate(selected, start=1):
        aq = models.AssessmentQuestion(
            version_id=version.id,
            question_id=q.id,
            sequence=idx,
            subject_id=q.subject_id,
            topic_id=q.topic_id,
            subtopic_id=q.subtopic_id,
            difficulty=q.difficulty,
            marks_available=marks_each,
        )
        db.add(aq)
        db.flush()
        snapshot_question_onto_aq(db, aq, q, marks_each, neg)

    a.status = "PUBLISHED"
    db.commit()

    # Notification isolated from publish success
    try:
        notif_svc.create_notification(
            db,
            event="ASSESSMENT_PUBLISHED",
            subject=f"Assessment published: {a.title}",
            body=f"Assessment '{a.title}' (type={a.assessment_type}) published for course_id={a.course_id}. Version v{next_ver}.",
            assessment_id=a.id,
            course_id=a.course_id,
            dispatch=True,
        )
    except Exception:
        pass

    return schemas.PublishResult(
        assessment_id=a.id,
        version_id=version.id,
        version_number=next_ver,
        question_count=len(selected),
        validation_errors=[],
    )


@router.post("/{assessment_id}/archive", response_model=schemas.AssessmentOut)
def archive_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = _load_assessment(db, assessment_id)
    require_assessment_designer(db, current_user, a.course_id)
    a.status = "ARCHIVED"
    db.commit()
    return _assessment_out(_load_assessment(db, a.id))
