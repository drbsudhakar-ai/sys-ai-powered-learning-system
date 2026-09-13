"""P036 governed academic-content authoring APIs."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import database, models, schemas
from app.routes.auth import require_roles
from app.services import academic_content as service

router = APIRouter(prefix="/academic-content", tags=["Academic Content"])
_staff = require_roles("admin", "faculty")
_admin = require_roles("admin")


def source_out(row):
    return {name: getattr(row, name) for name in ("id", "course_id", "subject_id", "source_code", "title",
        "source_type", "issuing_authority", "publication_date", "canonical_url", "rights_classification",
        "verification_status", "current_revision", "created_by", "verified_by", "verified_at", "created_at")}


def package_out(row, revision=None):
    data = {name: getattr(row, name) for name in ("id", "topic_id", "language", "status", "current_revision",
        "created_by", "approved_by", "approved_at", "created_at")}
    if revision:
        data["revision"] = {name: getattr(revision, name) for name in ("id", "revision", "objectives",
            "prerequisites", "concepts", "definitions", "formulas", "verified_facts", "worked_examples",
            "misconceptions", "exam_relevance", "subtopic_coverage", "source_revision_ids", "content_hash", "created_at")}
    return data


def profile_out(row):
    return {name: getattr(row, name) for name in ("id", "subject_id", "language", "version", "status",
        "teaching_strategy", "required_stage_types", "example_rules", "narration_rules", "visual_rules",
        "assessment_rules", "accuracy_constraints", "created_by", "approved_by", "approved_at", "created_at")}


@router.post("/sources", status_code=201)
def create_source(payload: schemas.AcademicSourceCreate, db: Session = Depends(database.get_db), actor=Depends(_staff)):
    return source_out(service.create_source(db, actor, payload))


@router.get("/courses/{course_id}/sources")
def list_sources(course_id: int, db: Session = Depends(database.get_db), actor=Depends(_staff)):
    course = db.get(models.Course, course_id)
    if not course: raise HTTPException(404, "Course not found")
    if (actor.role or "").lower() == "faculty" and not db.query(models.FacultyCourseAssignment.id).filter_by(
            faculty_id=actor.id, course_id=course_id).first() and not db.query(models.SubjectExpertAssignment.id).join(
            models.Subject).filter(models.SubjectExpertAssignment.faculty_id == actor.id,
            models.Subject.course_id == course_id).first():
        raise HTTPException(403, "Course content is outside your responsibility")
    return {"items": [source_out(row) for row in db.query(models.AcademicSource).filter_by(
        course_id=course_id).order_by(models.AcademicSource.source_code).all()]}


@router.post("/sources/{source_id}/decision")
def decide_source(source_id: int, payload: schemas.AcademicSourceDecision,
        db: Session = Depends(database.get_db), actor=Depends(_admin)):
    return source_out(service.decide_source(db, actor, source_id, payload))


@router.post("/knowledge-packages/revisions", status_code=201)
def create_knowledge_revision(payload: schemas.KnowledgePackageRevisionCreate,
        db: Session = Depends(database.get_db), actor=Depends(_staff)):
    package, revision = service.create_knowledge_revision(db, actor, payload)
    return package_out(package, revision)


@router.get("/topics/{topic_id}/knowledge-package")
def get_knowledge_package(topic_id: int, language: str = "en-IN",
        db: Session = Depends(database.get_db), actor=Depends(_staff)):
    topic, subject, _ = service.topic_scope(db, topic_id)
    reviewer = db.query(models.TopicAcademicReviewerAssignment.id).filter_by(
        topic_id=topic.id, faculty_id=actor.id, is_active=True).first()
    if not reviewer: service.require_manage_subject(db, actor, subject)
    package = db.query(models.TopicKnowledgePackage).filter_by(topic_id=topic.id, language=language).first()
    if not package: raise HTTPException(404, "Knowledge package not found")
    revision = db.query(models.TopicKnowledgeRevision).filter_by(
        package_id=package.id, revision=package.current_revision).first()
    return package_out(package, revision)


@router.post("/knowledge-packages/{package_id}/decision")
def decide_knowledge_package(package_id: int, payload: schemas.AcademicWorkflowDecision,
        db: Session = Depends(database.get_db), actor=Depends(_staff)):
    return package_out(service.decide_knowledge_package(db, actor, package_id, payload))


@router.put("/professor-profiles")
def upsert_professor_profile(payload: schemas.ProfessorProfileUpsert,
        db: Session = Depends(database.get_db), actor=Depends(_staff)):
    return profile_out(service.upsert_professor_profile(db, actor, payload))


@router.post("/professor-profiles/{profile_id}/approve")
def approve_professor_profile(profile_id: int, payload: schemas.AcademicSourceDecision,
        db: Session = Depends(database.get_db), actor=Depends(_admin)):
    if payload.action != "VERIFY": raise HTTPException(422, "Use VERIFY to approve a Professor Profile")
    return profile_out(service.approve_professor_profile(db, actor, profile_id, payload.comment))


@router.post("/reviewers", status_code=201)
def assign_reviewer(payload: schemas.TopicReviewerAssignmentCreate,
        db: Session = Depends(database.get_db), actor=Depends(_admin)):
    row = service.assign_reviewer(db, actor, payload)
    return {"id": row.id, "topic_id": row.topic_id, "faculty_id": row.faculty_id,
        "assigned_by": row.assigned_by, "is_active": row.is_active, "assigned_at": row.assigned_at}


@router.get("/reviewers/me")
def my_reviewer_assignments(db: Session = Depends(database.get_db), actor=Depends(_staff)):
    if (actor.role or "").lower() != "faculty": return {"items": []}
    rows = db.query(models.TopicAcademicReviewerAssignment).filter_by(
        faculty_id=actor.id, is_active=True).all()
    return {"items": [{"id": row.id, "topic_id": row.topic_id,
        "topic_name": db.get(models.Topic, row.topic_id).name, "assigned_at": row.assigned_at} for row in rows]}


@router.get("/courses/{course_id}/benchmark-readiness")
def benchmark_readiness(course_id: int, db: Session = Depends(database.get_db), actor=Depends(_staff)):
    return service.benchmark_readiness(db, actor, course_id)
