"""Governed academic sources, knowledge packages, professor profiles and reviewers."""
import hashlib
import json
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import models


def _hash(value) -> str:
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def topic_scope(db: Session, topic_id: int):
    topic = db.get(models.Topic, topic_id)
    if not topic or not topic.subject or not topic.subject.course_id:
        raise HTTPException(404, "Topic or owning course not found")
    return topic, topic.subject, topic.subject.course_id


def can_manage_subject(db: Session, actor, subject) -> bool:
    if (actor.role or "").lower() in {"admin", "super_admin"}:
        return True
    if (actor.role or "").lower() != "faculty" or not actor.is_active:
        return False
    coordinator = db.query(models.FacultyCourseAssignment.id).filter_by(
        faculty_id=actor.id, course_id=subject.course_id).first()
    expert = db.query(models.SubjectExpertAssignment.id).filter_by(
        faculty_id=actor.id, subject_id=subject.id).first()
    return bool(coordinator or expert)


def require_manage_subject(db, actor, subject):
    if not can_manage_subject(db, actor, subject):
        raise HTTPException(403, "This academic content is outside your assigned responsibility")


def require_manage_course(db: Session, actor, course_id: int):
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    role = (actor.role or "").lower()
    if role in {"admin", "super_admin"}:
        return course
    coordinator = role == "faculty" and actor.is_active and db.query(
        models.FacultyCourseAssignment.id).filter_by(
        faculty_id=actor.id, course_id=course_id).first()
    if not coordinator:
        raise HTTPException(403, "Course Knowledge Studio is restricted to administrators and the assigned coordinator")
    return course


def _audit(db, actor, action, target_type, target_id, summary, **details):
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action=action,
        target_type=target_type, target_id=target_id, summary=summary[:255], details=details))


def create_source(db, actor, payload):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    subject = db.get(models.Subject, payload.subject_id) if payload.subject_id else None
    if subject and subject.course_id != course.id:
        raise HTTPException(422, "Source subject does not belong to the selected course")
    if subject:
        require_manage_subject(db, actor, subject)
    elif (actor.role or "").lower() not in {"admin", "super_admin"} and not db.query(
            models.FacultyCourseAssignment.id).filter_by(faculty_id=actor.id, course_id=course.id).first():
        raise HTTPException(403, "Only the course coordinator can create a course-wide source")
    code = payload.source_code.strip().upper()
    if db.query(models.AcademicSource.id).filter_by(course_id=course.id, source_code=code).first():
        raise HTTPException(409, "Source code already exists in this course")
    source = models.AcademicSource(course_id=course.id, subject_id=subject.id if subject else None,
        source_code=code, title=payload.title.strip(), source_type=payload.source_type,
        issuing_authority=payload.issuing_authority, publication_date=payload.publication_date,
        canonical_url=payload.canonical_url, rights_classification=payload.rights_classification,
        verification_status="DRAFT", current_revision=1, created_by=actor.id)
    db.add(source); db.flush()
    revision = models.AcademicSourceRevision(source_id=source.id, revision=1,
        content_text=payload.content_text.strip(), content_hash=_hash(payload.content_text.strip()),
        notes=payload.revision_notes, created_by=actor.id)
    db.add(revision)
    _audit(db, actor, "academic_source.create", "academic_source", source.id,
        f"Created academic source {code}", changed_fields=["source", "revision"])
    db.commit(); db.refresh(source)
    return source


def decide_source(db, actor, source_id, payload):
    source = db.get(models.AcademicSource, source_id)
    if not source: raise HTTPException(404, "Academic source not found")
    if (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator verification is required")
    source.verification_status = "VERIFIED" if payload.action == "VERIFY" else "REJECTED"
    source.verified_by = actor.id; source.verified_at = datetime.now(timezone.utc)
    _audit(db, actor, f"academic_source.{payload.action.lower()}", "academic_source", source.id,
        f"{payload.action.title()} academic source {source.source_code}", comment=payload.comment)
    db.commit(); db.refresh(source); return source


def create_knowledge_revision(db, actor, payload):
    topic, subject, course_id = topic_scope(db, payload.topic_id)
    require_manage_subject(db, actor, subject)
    revisions = db.query(models.AcademicSourceRevision).join(models.AcademicSource).filter(
        models.AcademicSourceRevision.id.in_(payload.source_revision_ids),
        models.AcademicSource.course_id == course_id,
        models.AcademicSource.verification_status == "VERIFIED").all()
    if len({row.id for row in revisions}) != len(set(payload.source_revision_ids)):
        raise HTTPException(422, "Every knowledge source revision must be verified and belong to this course")
    package = db.query(models.TopicKnowledgePackage).filter_by(topic_id=topic.id, language=payload.language).first()
    if not package:
        package = models.TopicKnowledgePackage(topic_id=topic.id, language=payload.language,
            status="DRAFT", current_revision=0, created_by=actor.id)
        db.add(package); db.flush()
    if package.status == "APPROVED":
        package.status = "DRAFT"; package.approved_by = None; package.approved_at = None
    revision_number = package.current_revision + 1
    content = payload.model_dump(exclude={"topic_id", "language"})
    revision = models.TopicKnowledgeRevision(package_id=package.id, revision=revision_number,
        content_hash=_hash(content), created_by=actor.id, **content)
    package.current_revision = revision_number
    db.add(revision)
    _audit(db, actor, "knowledge_package.revise", "topic_knowledge_package", package.id,
        f"Created knowledge revision {revision_number} for {topic.name}", revision=revision_number)
    db.commit(); db.refresh(package)
    return package, revision


TRANSITIONS = {
    ("DRAFT", "SUBMIT"): "SOURCE_REVIEW", ("CHANGES_REQUESTED", "SUBMIT"): "SOURCE_REVIEW",
    ("SOURCE_REVIEW", "EXPERT_VERIFY"): "EXPERT_VERIFIED",
    ("SOURCE_REVIEW", "REQUEST_CHANGES"): "CHANGES_REQUESTED",
    ("EXPERT_VERIFIED", "REQUEST_CHANGES"): "CHANGES_REQUESTED",
    ("EXPERT_VERIFIED", "APPROVE"): "APPROVED", ("APPROVED", "SUPERSEDE"): "SUPERSEDED",
}


def decide_knowledge_package(db, actor, package_id, payload):
    package = db.get(models.TopicKnowledgePackage, package_id)
    if not package: raise HTTPException(404, "Knowledge package not found")
    topic, subject, _ = topic_scope(db, package.topic_id)
    require_manage_subject(db, actor, subject)
    previous_status = package.status
    target = TRANSITIONS.get((previous_status, payload.action))
    if not target: raise HTTPException(409, f"Cannot {payload.action.lower()} a {package.status} package")
    if payload.action in {"APPROVE", "SUPERSEDE"} and (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator approval is required")
    if payload.action == "EXPERT_VERIFY":
        expert = db.query(models.SubjectExpertAssignment.id).filter_by(
            faculty_id=actor.id, subject_id=subject.id).first()
        if not expert and (actor.role or "").lower() not in {"admin", "super_admin"}:
            raise HTTPException(403, "Assigned Subject Expert verification is required")
    package.status = target
    if target == "APPROVED":
        package.approved_by = actor.id; package.approved_at = datetime.now(timezone.utc)
    _audit(db, actor, f"knowledge_package.{payload.action.lower()}", "topic_knowledge_package", package.id,
        f"{payload.action.title()} knowledge package for {topic.name}", comment=payload.comment,
        from_status=previous_status, to_status=target)
    db.commit(); db.refresh(package); return package


def upsert_professor_profile(db, actor, payload):
    subject = db.get(models.Subject, payload.subject_id)
    if not subject: raise HTTPException(404, "Subject not found")
    require_manage_subject(db, actor, subject)
    profile = db.query(models.SubjectProfessorProfile).filter_by(
        subject_id=subject.id, language=payload.language).first()
    if not profile:
        profile = models.SubjectProfessorProfile(subject_id=subject.id, language=payload.language,
            version=1, created_by=actor.id)
        db.add(profile)
    else:
        profile.version += 1; profile.status = "DRAFT"; profile.approved_by = None; profile.approved_at = None
    for name, value in payload.model_dump(exclude={"subject_id", "language"}).items(): setattr(profile, name, value)
    db.flush()
    _audit(db, actor, "professor_profile.revise", "subject_professor_profile", profile.id,
        f"Revised Professor Profile for {subject.name}", version=profile.version)
    db.commit(); db.refresh(profile); return profile


def approve_professor_profile(db, actor, profile_id, comment):
    profile = db.get(models.SubjectProfessorProfile, profile_id)
    if not profile: raise HTTPException(404, "Professor Profile not found")
    if (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator approval is required")
    profile.status = "APPROVED"; profile.approved_by = actor.id; profile.approved_at = datetime.now(timezone.utc)
    _audit(db, actor, "professor_profile.approve", "subject_professor_profile", profile.id,
        "Approved Subject Professor Profile", comment=comment)
    db.commit(); db.refresh(profile); return profile


def assign_reviewer(db, actor, payload):
    topic, subject, _ = topic_scope(db, payload.topic_id)
    if (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator assignment is required")
    faculty = db.get(models.User, payload.faculty_id)
    if not faculty or (faculty.role or "").lower() != "faculty" or not faculty.is_active:
        raise HTTPException(422, "Select an active faculty member")
    other_benchmark = db.query(models.TopicAcademicReviewerAssignment).join(
        models.Topic, models.Topic.id == models.TopicAcademicReviewerAssignment.topic_id).filter(
        models.Topic.subject_id == subject.id,
        models.TopicAcademicReviewerAssignment.is_active.is_(True),
        models.TopicAcademicReviewerAssignment.topic_id != topic.id).first()
    if other_benchmark:
        raise HTTPException(409, "This subject already has a different active benchmark topic")
    row = db.query(models.TopicAcademicReviewerAssignment).filter_by(
        topic_id=topic.id, faculty_id=faculty.id).first()
    if row: row.is_active = True
    else:
        row = models.TopicAcademicReviewerAssignment(topic_id=topic.id, faculty_id=faculty.id,
            assigned_by=actor.id, is_active=True); db.add(row)
    db.flush()
    _audit(db, actor, "academic_reviewer.assign", "topic", topic.id,
        f"Assigned academic reviewer for {topic.name}", faculty_id=faculty.id)
    db.commit(); db.refresh(row); return row


def benchmark_readiness(db, actor, course_id):
    course = db.get(models.Course, course_id)
    if not course: raise HTTPException(404, "Course not found")
    if (actor.role or "").lower() == "faculty" and not db.query(models.FacultyCourseAssignment.id).filter_by(
            faculty_id=actor.id, course_id=course_id).first():
        raise HTTPException(403, "Course benchmark readiness is restricted to its coordinator")
    subjects = db.query(models.Subject).filter_by(course_id=course_id).order_by(models.Subject.sequence, models.Subject.id).all()
    items = []
    for subject in subjects:
        assignments = db.query(models.TopicAcademicReviewerAssignment).join(models.Topic).filter(
            models.Topic.subject_id == subject.id,
            models.TopicAcademicReviewerAssignment.is_active.is_(True)).all()
        topic_ids = sorted({row.topic_id for row in assignments})
        topic_id = topic_ids[0] if len(topic_ids) == 1 else None
        package = db.query(models.TopicKnowledgePackage).filter_by(
            topic_id=topic_id, language="en-IN").first() if topic_id else None
        profile = db.query(models.SubjectProfessorProfile).filter_by(
            subject_id=subject.id, language="en-IN").first()
        items.append({"subject_id": subject.id, "subject_name": subject.name,
            "benchmark_topic_id": topic_id,
            "benchmark_topic_name": db.get(models.Topic, topic_id).name if topic_id else None,
            "reviewer_count": len(assignments),
            "knowledge_status": package.status if package else "NOT_PREPARED",
            "professor_profile_status": profile.status if profile else "NOT_PREPARED",
            "ready": bool(topic_id and assignments and package and package.status == "APPROVED"
                and profile and profile.status == "APPROVED")})
    return {"course_id": course_id, "subject_count": len(subjects),
        "ready_subject_count": sum(item["ready"] for item in items),
        "ready": bool(subjects) and all(item["ready"] for item in items), "items": items}


COURSE_POLICY_FIELDS = (
    "audience", "teaching_objective", "default_language", "required_lesson_stages",
    "delivery_requirements", "accuracy_requirements",
)


def save_teaching_pack_revision(db, actor, course_id, payload):
    require_manage_course(db, actor, course_id)
    pack = db.query(models.CourseTeachingPack).filter_by(
        course_id=course_id, language=payload.language).first()
    if not pack:
        pack = models.CourseTeachingPack(course_id=course_id, language=payload.language,
            status="DRAFT", current_revision=0, created_by=actor.id)
        db.add(pack); db.flush()
    revision_number = pack.current_revision + 1
    policy = payload.course_policy
    revision = models.CourseTeachingPackRevision(teaching_pack_id=pack.id,
        revision=revision_number, status="DRAFT", course_policy=policy,
        validation_report={}, content_hash=_hash(policy), revision_notes=payload.revision_notes,
        created_by=actor.id)
    pack.current_revision = revision_number
    if pack.status != "ACTIVE":
        pack.status = "DRAFT"
    db.add(revision)
    _audit(db, actor, "teaching_pack.revise", "course_teaching_pack", pack.id,
        f"Created Course Teaching Pack revision {revision_number}", revision=revision_number)
    db.commit(); db.refresh(pack); db.refresh(revision)
    return pack, revision


def _teaching_pack_validation(db, pack, revision):
    errors = []
    policy = revision.course_policy or {}
    for field in COURSE_POLICY_FIELDS:
        value = policy.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"Course policy field '{field}' is required")
    subjects = db.query(models.Subject).filter_by(course_id=pack.course_id).all()
    if not subjects:
        errors.append("The course has no saved subjects")
    profiles = db.query(models.SubjectProfessorProfile).filter(
        models.SubjectProfessorProfile.subject_id.in_([row.id for row in subjects]),
        models.SubjectProfessorProfile.language == pack.language).all() if subjects else []
    profile_subject_ids = {row.subject_id for row in profiles}
    for subject in subjects:
        if subject.id not in profile_subject_ids:
            errors.append(f"Subject Delivery Guide is missing for {subject.name}")
    return {"valid": not errors, "errors": errors,
        "subject_count": len(subjects), "subject_guides": len(profile_subject_ids),
        "validated_at": datetime.now(timezone.utc).isoformat()}


def decide_teaching_pack(db, actor, course_id, revision_number, payload):
    pack = db.query(models.CourseTeachingPack).filter_by(course_id=course_id).first()
    if not pack:
        raise HTTPException(404, "Course Teaching Pack not found")
    revision = db.query(models.CourseTeachingPackRevision).filter_by(
        teaching_pack_id=pack.id, revision=revision_number).first()
    if not revision:
        raise HTTPException(404, "Course Teaching Pack revision not found")
    require_manage_course(db, actor, course_id)
    report = _teaching_pack_validation(db, pack, revision)
    revision.validation_report = report
    if payload.action == "VALIDATE":
        revision.status = "VALIDATED" if report["valid"] else "NEEDS_CORRECTION"
        if revision_number == pack.current_revision and pack.status != "ACTIVE":
            pack.status = revision.status
    else:
        if (actor.role or "").lower() not in {"admin", "super_admin"}:
            raise HTTPException(403, "Administrator activation is required")
        if not report["valid"]:
            revision.status = "NEEDS_CORRECTION"
            db.commit()
            raise HTTPException(409, {"message": "Teaching Pack validation failed", "errors": report["errors"]})
        db.query(models.CourseTeachingPackRevision).filter(
            models.CourseTeachingPackRevision.teaching_pack_id == pack.id,
            models.CourseTeachingPackRevision.status == "ACTIVE").update({"status": "SUPERSEDED"})
        now = datetime.now(timezone.utc)
        revision.status = "ACTIVE"; revision.activated_by = actor.id; revision.activated_at = now
        pack.status = "ACTIVE"; pack.active_revision = revision.revision
        pack.activated_by = actor.id; pack.activated_at = now
        subject_ids = [row[0] for row in db.query(models.Subject.id).filter_by(course_id=course_id).all()]
        if subject_ids:
            db.query(models.SubjectProfessorProfile).filter(
                models.SubjectProfessorProfile.subject_id.in_(subject_ids),
                models.SubjectProfessorProfile.language == pack.language).update({
                    "status": "APPROVED", "approved_by": actor.id, "approved_at": now},
                    synchronize_session=False)
    _audit(db, actor, f"teaching_pack.{payload.action.lower()}", "course_teaching_pack", pack.id,
        f"{payload.action.title()} Course Teaching Pack revision {revision.revision}",
        comment=payload.comment, validation=report)
    db.commit(); db.refresh(pack); db.refresh(revision)
    return pack, revision


def course_knowledge_studio(db, actor, course_id, language="en-IN"):
    course = require_manage_course(db, actor, course_id)
    pack = db.query(models.CourseTeachingPack).filter_by(course_id=course_id, language=language).first()
    revision = db.query(models.CourseTeachingPackRevision).filter_by(
        teaching_pack_id=pack.id, revision=pack.current_revision).first() if pack else None
    subjects = db.query(models.Subject).filter_by(course_id=course_id).order_by(
        models.Subject.sequence, models.Subject.id).all()
    items = []
    totals = {"subjects": len(subjects), "units": 0, "topics": 0, "subtopics": 0,
        "topic_packages": 0, "approved_topic_packages": 0, "covered_subtopics": 0}
    for subject in subjects:
        units = db.query(models.Unit).filter_by(subject_id=subject.id).count()
        topic_rows = db.query(models.Topic).filter_by(subject_id=subject.id).all()
        topic_ids = [row.id for row in topic_rows]
        subtopics = db.query(models.Subtopic).filter(models.Subtopic.topic_id.in_(topic_ids)).count() if topic_ids else 0
        packages = db.query(models.TopicKnowledgePackage).filter(
            models.TopicKnowledgePackage.topic_id.in_(topic_ids),
            models.TopicKnowledgePackage.language == language).all() if topic_ids else []
        approved = [row for row in packages if row.status == "APPROVED"]
        covered_subtopics = set()
        for package in packages:
            package_revision = db.query(models.TopicKnowledgeRevision).filter_by(
                package_id=package.id, revision=package.current_revision).first()
            for entry in (package_revision.subtopic_coverage if package_revision else []) or []:
                value = entry.get("subtopic_id") if isinstance(entry, dict) else entry
                if value: covered_subtopics.add(value)
        profile = db.query(models.SubjectProfessorProfile).filter_by(
            subject_id=subject.id, language=language).first()
        items.append({"subject_id": subject.id, "subject_name": subject.name,
            "unit_count": units, "topic_count": len(topic_ids), "subtopic_count": subtopics,
            "topic_package_count": len(packages), "approved_topic_package_count": len(approved),
            "covered_subtopic_count": len(covered_subtopics),
            "delivery_guide": profile_out_dict(profile) if profile else None})
        totals["units"] += units; totals["topics"] += len(topic_ids); totals["subtopics"] += subtopics
        totals["topic_packages"] += len(packages); totals["approved_topic_packages"] += len(approved)
        totals["covered_subtopics"] += len(covered_subtopics)
    provider = db.get(models.AIProviderSettings, 1)
    return {"course": {"id": course.id, "title": course.title, "programme_code": course.programme_code,
            "publication_status": str(course.publication_status).split(".")[-1]},
        "access_mode": "ADMINISTRATOR" if (actor.role or "").lower() in {"admin", "super_admin"} else "COURSE_COORDINATOR",
        "teaching_pack": {"id": pack.id, "language": pack.language, "status": pack.status,
            "current_revision": pack.current_revision, "active_revision": pack.active_revision,
            "course_policy": revision.course_policy if revision else {},
            "validation_report": revision.validation_report if revision else {}} if pack else None,
        "coverage": totals, "subjects": items,
        "future_capabilities": {"external_import": "P036.2B", "ai_generation": "P036.2C"},
        "provider": {"configured": bool(provider), "enabled": bool(provider and provider.enabled),
            "label": provider.label if provider else None, "model": provider.model if provider else None,
            "max_output_tokens": provider.max_output_tokens if provider else None}}


def profile_out_dict(row):
    return {name: getattr(row, name) for name in ("id", "subject_id", "language", "version", "status",
        "teaching_strategy", "required_stage_types", "example_rules", "narration_rules", "visual_rules",
        "assessment_rules", "accuracy_constraints")} if row else None
