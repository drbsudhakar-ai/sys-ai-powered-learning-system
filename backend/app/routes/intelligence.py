"""Historical papers, weightage, selection, AI Lecturer intelligence APIs (P0-010)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.academic_auth import require_assessment_designer, require_question_author, can_access_course_questions, is_admin
from app.routes.auth import get_current_user, require_roles
from app.services import question_intelligence as qi
from app.services import selection_engine as sel
from app.services.similarity import fingerprint

router = APIRouter(tags=["Question Intelligence"])
_staff = require_roles("admin", "faculty")
_admin = require_roles("admin")


# ---------- Historical papers ----------
@router.get("/historical-papers", response_model=List[schemas.HistoricalPaperOut])
def list_papers(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    q = db.query(models.HistoricalExamPaper)
    if course_id is not None:
        if not can_access_course_questions(db, current_user, course_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        q = q.filter(models.HistoricalExamPaper.course_id == course_id)
    return q.order_by(models.HistoricalExamPaper.exam_year.desc()).all()


@router.post("/historical-papers", response_model=schemas.HistoricalPaperOut, status_code=201)
def create_paper(
    payload: schemas.HistoricalPaperCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_assessment_designer(db, current_user, payload.course_id)
    paper = models.HistoricalExamPaper(
        exam_name=payload.exam_name,
        exam_year=payload.exam_year,
        course_id=payload.course_id,
        exam_type=payload.exam_type,
        source=payload.source,
    )
    db.add(paper)
    db.flush()
    for hq in payload.questions or []:
        db.add(
            models.HistoricalExamQuestion(
                paper_id=paper.id,
                subject_id=hq.subject_id,
                topic_id=hq.topic_id,
                subtopic_id=hq.subtopic_id,
                question_text=hq.question_text,
                question_type=hq.question_type,
                marks=hq.marks,
                difficulty=hq.difficulty,
                concept_tags=hq.concept_tags,
                linked_question_id=hq.linked_question_id,
                similarity_class=hq.similarity_class or "CONCEPT_VARIANT",
                fingerprint=fingerprint(hq.question_text),
            )
        )
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/historical-papers/{paper_id}", response_model=schemas.HistoricalPaperDetailOut)
def get_paper(
    paper_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    paper = db.query(models.HistoricalExamPaper).filter(models.HistoricalExamPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not can_access_course_questions(db, current_user, paper.course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return schemas.HistoricalPaperDetailOut(
        id=paper.id,
        exam_name=paper.exam_name,
        exam_year=paper.exam_year,
        course_id=paper.course_id,
        exam_type=paper.exam_type,
        source=paper.source,
        created_at=paper.created_at,
        questions=[schemas.HistoricalQuestionOut.model_validate(q) for q in paper.questions],
    )


@router.post("/historical-analysis/{course_id}")
def run_historical_analysis(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_assessment_designer(db, current_user, course_id)
    analysis = qi.analyze_course_history(db, course_id)
    snaps = qi.compute_and_store_topic_priorities(db, course_id)
    return {
        "analysis": analysis,
        "topic_priorities": [
            {
                "topic_id": s.topic_id,
                "priority_score": s.priority_score,
                "priority_label": s.priority_label,
                "historical_frequency": s.historical_frequency,
                "avg_marks_weightage": s.avg_marks_weightage,
                "recent_trend": s.recent_trend,
                "contributing_factors": s.contributing_factors,
                "question_count": s.question_count,
            }
            for s in snaps
        ],
    }


# ---------- Weightage ----------
@router.get("/weightages/subjects")
def list_subject_weightages(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    if not can_access_course_questions(db, current_user, course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    rows = db.query(models.SubjectWeightage).filter(models.SubjectWeightage.course_id == course_id).all()
    return [
        {"id": r.id, "course_id": r.course_id, "subject_id": r.subject_id, "weight_percent": r.weight_percent}
        for r in rows
    ]


@router.put("/weightages/subjects")
def set_subject_weightages(
    payload: schemas.SubjectWeightageBulk,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_assessment_designer(db, current_user, payload.course_id)
    total = sum(i.weight_percent for i in payload.items)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(status_code=422, detail=f"Subject weightages must sum to 100 (got {total})")
    db.query(models.SubjectWeightage).filter(
        models.SubjectWeightage.course_id == payload.course_id
    ).delete()
    for item in payload.items:
        db.add(
            models.SubjectWeightage(
                course_id=payload.course_id,
                subject_id=item.subject_id,
                weight_percent=item.weight_percent,
            )
        )
    db.commit()
    return {"ok": True, "total": total}


@router.put("/weightages/topics")
def set_topic_weightages(
    payload: schemas.TopicWeightageBulk,
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
    total = sum(i.weight_percent for i in payload.items)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(status_code=422, detail=f"Topic weightages must sum to 100 (got {total})")
    db.query(models.TopicWeightage).filter(models.TopicWeightage.subject_id == payload.subject_id).delete()
    for item in payload.items:
        db.add(
            models.TopicWeightage(
                subject_id=payload.subject_id,
                topic_id=item.topic_id,
                weight_percent=item.weight_percent,
                syllabus_importance=item.syllabus_importance if item.syllabus_importance is not None else 0.5,
            )
        )
    db.commit()
    return {"ok": True, "total": total}


@router.get("/weightages/topics")
def list_topic_weightages(
    subject_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    rows = db.query(models.TopicWeightage).filter(models.TopicWeightage.subject_id == subject_id).all()
    return [
        {
            "id": r.id,
            "subject_id": r.subject_id,
            "topic_id": r.topic_id,
            "weight_percent": r.weight_percent,
            "syllabus_importance": r.syllabus_importance,
        }
        for r in rows
    ]


@router.put("/priority-weights/{course_id}")
def set_priority_weights(
    course_id: int,
    payload: schemas.PriorityWeightsIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_assessment_designer(db, current_user, course_id)
    vals = payload.model_dump()
    total = sum(vals.values())
    if abs(total - 1.0) > 0.02:
        raise HTTPException(status_code=422, detail=f"Priority weights must sum to 1.0 (got {total})")
    cfg = (
        db.query(models.PriorityWeightConfig)
        .filter(models.PriorityWeightConfig.course_id == course_id)
        .first()
    )
    if not cfg:
        cfg = models.PriorityWeightConfig(course_id=course_id)
        db.add(cfg)
    for k, v in vals.items():
        setattr(cfg, k, v)
    db.commit()
    return {"ok": True, "weights": vals}


# ---------- Intelligence ----------
@router.get("/academic-intelligence/topics/{topic_id}")
def ai_lecturer_topic_intelligence(
    topic_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Stable contract for AI Lecturer (staff or authenticated consumers)."""
    payload = qi.topic_intelligence_payload(db, topic_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Topic not found")
    return payload


@router.get("/academic-intelligence/questions/{question_id}/importance")
def question_importance_api(
    question_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if not can_access_course_questions(db, current_user, q.course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return qi.question_importance(db, q)


@router.get("/academic-intelligence/courses/{course_id}/topics")
def list_topic_intelligence(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    if not can_access_course_questions(db, current_user, course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    snaps = (
        db.query(models.TopicIntelligenceSnapshot)
        .filter(models.TopicIntelligenceSnapshot.course_id == course_id)
        .all()
    )
    if not snaps:
        snaps = qi.compute_and_store_topic_priorities(db, course_id)
    topics = {t.id: t for t in db.query(models.Topic).all()}
    return [
        {
            "topic_id": s.topic_id,
            "topic_name": topics[s.topic_id].name if s.topic_id in topics else None,
            "priority": s.priority_label,
            "priority_score": s.priority_score,
            "historical_frequency": s.historical_frequency,
            "weightage": s.avg_marks_weightage,
            "trend": s.recent_trend,
            "question_count": s.question_count,
            "contributing_factors": s.contributing_factors,
        }
        for s in snaps
    ]


@router.post("/question-selection")
def question_selection(
    payload: schemas.SelectionRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_assessment_designer(db, current_user, payload.course_id)
    result = sel.select_questions(
        db,
        course_id=payload.course_id,
        total_questions=payload.total_questions,
        subject_distribution=payload.subject_distribution,
        topic_ids=payload.topic_ids,
        difficulty_distribution=payload.difficulty_distribution,
        question_types=payload.question_types,
        reuse_policy=payload.reuse_policy or "MIXED",
        reuse_mix=payload.reuse_mix,
        evidence_based=payload.evidence_based if payload.evidence_based is not None else True,
    )
    return {
        "selected": result["selected"],
        "errors": result["errors"],
        "pool_size": result["pool_size"],
        "disclaimer": result["disclaimer"],
    }


@router.get("/question-bank/stats")
def question_bank_stats(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    if not can_access_course_questions(db, current_user, course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    rows = db.query(models.Question).filter(models.Question.course_id == course_id).all()
    by_subject = {}
    by_topic = {}
    by_diff = {}
    by_status = {}
    by_type = {}
    for r in rows:
        by_subject[r.subject_id] = by_subject.get(r.subject_id, 0) + 1
        if r.topic_id:
            by_topic[r.topic_id] = by_topic.get(r.topic_id, 0) + 1
        by_diff[r.difficulty] = by_diff.get(r.difficulty, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_type[r.question_type] = by_type.get(r.question_type, 0) + 1
    return {
        "total": len(rows),
        "by_subject": by_subject,
        "by_topic": by_topic,
        "by_difficulty": by_diff,
        "by_status": by_status,
        "by_type": by_type,
    }
