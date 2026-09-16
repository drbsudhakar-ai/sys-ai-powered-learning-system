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
    ("PILOT_APPROVED", "SUBMIT"): "SOURCE_REVIEW",
    ("SOURCE_REVIEW", "EXPERT_VERIFY"): "EXPERT_VERIFIED",
    ("SOURCE_REVIEW", "REQUEST_CHANGES"): "CHANGES_REQUESTED",
    ("EXPERT_VERIFIED", "REQUEST_CHANGES"): "CHANGES_REQUESTED",
    ("EXPERT_VERIFIED", "APPROVE"): "APPROVED", ("APPROVED", "SUPERSEDE"): "SUPERSEDED",
}


def decide_knowledge_package(db, actor, package_id, payload):
    package = db.get(models.TopicKnowledgePackage, package_id)
    if not package: raise HTTPException(404, "Knowledge package not found")
    topic, subject, _ = topic_scope(db, package.topic_id)
    assigned_reviewer = db.query(models.TopicAcademicReviewerAssignment.id).filter_by(
        topic_id=topic.id, faculty_id=actor.id, is_active=True).first()
    if not (assigned_reviewer and payload.action in {"EXPERT_VERIFY", "REQUEST_CHANGES"}):
        require_manage_subject(db, actor, subject)
    previous_status = package.status
    target = TRANSITIONS.get((previous_status, payload.action))
    if not target: raise HTTPException(409, f"Cannot {payload.action.lower()} a {package.status} package")
    if payload.action in {"APPROVE", "SUPERSEDE"} and (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator approval is required")
    if payload.action == "EXPERT_VERIFY":
        expert = db.query(models.SubjectExpertAssignment.id).filter_by(
            faculty_id=actor.id, subject_id=subject.id).first()
        if not expert and not assigned_reviewer and (actor.role or "").lower() not in {"admin", "super_admin"}:
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


def knowledge_review_workspace(db, actor, course_id):
    course = db.get(models.Course, course_id)
    if not course: raise HTTPException(404, "Course not found")
    role = (actor.role or "").lower()
    assigned_topic_ids = None
    if role == "faculty":
        assigned_topic_ids = {row[0] for row in db.query(models.TopicAcademicReviewerAssignment.topic_id).filter_by(
            faculty_id=actor.id, is_active=True).all()}
        coordinator = db.query(models.FacultyCourseAssignment.id).filter_by(
            faculty_id=actor.id, course_id=course_id).first()
        if not assigned_topic_ids and not coordinator:
            raise HTTPException(403, "No academic review responsibility is assigned in this course")
    packages = db.query(models.TopicKnowledgePackage).join(models.Topic).join(models.Subject).filter(
        models.Subject.course_id == course_id).order_by(models.Subject.sequence, models.Topic.sequence).all()
    items = []
    for package in packages:
        if assigned_topic_ids is not None and package.topic_id not in assigned_topic_ids:
            continue
        topic = db.get(models.Topic, package.topic_id); subject = topic.subject
        revision = db.query(models.TopicKnowledgeRevision).filter_by(
            package_id=package.id, revision=package.current_revision).first()
        assignments = db.query(models.TopicAcademicReviewerAssignment).filter_by(
            topic_id=topic.id, is_active=True).all()
        reviewers = []
        for assignment in assignments:
            faculty = db.get(models.User, assignment.faculty_id)
            reviewers.append({"assignment_id": assignment.id, "faculty_id": assignment.faculty_id,
                "faculty_name": faculty.name if faculty else "Unavailable faculty",
                "faculty_email": faculty.email if faculty else None})
        items.append({"package_id": package.id, "topic_id": topic.id, "topic_name": topic.name,
            "subject_id": subject.id, "subject_name": subject.name, "language": package.language,
            "status": package.status, "current_revision": package.current_revision,
            "reviewers": reviewers, "revision": {name: getattr(revision, name) for name in (
                "objectives", "prerequisites", "concepts", "definitions", "formulas", "verified_facts",
                "worked_examples", "misconceptions", "exam_relevance", "subtopic_coverage",
                "source_revision_ids", "content_hash")} if revision else None})
    counts = {status: sum(item["status"] == status for item in items) for status in (
        "DRAFT", "SOURCE_REVIEW", "EXPERT_VERIFIED", "CHANGES_REQUESTED", "PILOT_APPROVED", "APPROVED")}
    return {"course_id": course.id, "course_title": course.title, "items": items, "counts": counts,
        "ready": bool(items) and all(item["status"] == "APPROVED" for item in items),
        "can_administer": role in {"admin", "super_admin"}}


def my_knowledge_reviews(db, actor):
    if (actor.role or "").lower() != "faculty":
        raise HTTPException(403, "Faculty reviewer access is required")
    course_ids = {row[0] for row in db.query(models.Subject.course_id).join(
        models.Topic, models.Topic.subject_id == models.Subject.id).join(
        models.TopicAcademicReviewerAssignment,
        models.TopicAcademicReviewerAssignment.topic_id == models.Topic.id).filter(
        models.TopicAcademicReviewerAssignment.faculty_id == actor.id,
        models.TopicAcademicReviewerAssignment.is_active.is_(True)).all()}
    courses = [knowledge_review_workspace(db, actor, course_id) for course_id in sorted(course_ids)]
    return {"courses": courses, "assignment_count": sum(len(course["items"]) for course in courses)}


def _pilot_package_check(db, package):
    revision = db.query(models.TopicKnowledgeRevision).filter_by(
        package_id=package.id, revision=package.current_revision).first()
    errors = []
    if not revision: return ["Current revision is missing"]
    for field in ("objectives", "concepts", "worked_examples", "misconceptions", "exam_relevance", "source_revision_ids"):
        if not getattr(revision, field, None): errors.append(f"{field.replace('_', ' ').title()} is missing")
    topic_subtopics = {row.id for row in db.query(models.Subtopic).filter_by(topic_id=package.topic_id)}
    covered = {entry.get("subtopic_id") for entry in (revision.subtopic_coverage or []) if isinstance(entry, dict)}
    if topic_subtopics - covered: errors.append(f"{len(topic_subtopics - covered)} syllabus subtopics are not covered")
    verified_sources = db.query(models.AcademicSource.id).join(models.AcademicSourceRevision).filter(
        models.AcademicSourceRevision.id.in_(revision.source_revision_ids or []),
        models.AcademicSource.verification_status == "VERIFIED").count()
    if verified_sources != len(set(revision.source_revision_ids or [])): errors.append("Every source revision must be verified")
    return errors


def pilot_knowledge_approval_preview(db, actor, course_id):
    course = require_manage_course(db, actor, course_id)
    if (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator pilot approval is required")
    packages = db.query(models.TopicKnowledgePackage).join(models.Topic).join(models.Subject).filter(
        models.Subject.course_id == course_id).order_by(models.Subject.sequence, models.Topic.sequence).all()
    items = []
    for package in packages:
        topic = db.get(models.Topic, package.topic_id); errors = _pilot_package_check(db, package)
        items.append({"package_id": package.id, "subject_name": topic.subject.name, "topic_name": topic.name,
            "status": package.status, "eligible": not errors and package.status in {"DRAFT", "CHANGES_REQUESTED"},
            "errors": errors})
    eligible = [item for item in items if item["eligible"]]
    return {"course_id": course.id, "course_code": course.programme_code, "package_count": len(items),
        "eligible_count": len(eligible), "expected_package_ids": [item["package_id"] for item in eligible],
        "items": items, "declaration": "Pilot approval permits controlled demonstration only; independent expert verification and institutional approval remain pending."}


def pilot_approve_knowledge_packages(db, actor, course_id, payload):
    preview = pilot_knowledge_approval_preview(db, actor, course_id)
    if payload.course_code.strip() != (preview["course_code"] or ""):
        raise HTTPException(422, "Enter the exact course code to confirm pilot approval")
    if sorted(set(payload.expected_package_ids)) != sorted(preview["expected_package_ids"]):
        raise HTTPException(409, "Eligible packages changed; refresh the pilot approval preview")
    now = datetime.now(timezone.utc)
    for package_id in preview["expected_package_ids"]:
        package = db.get(models.TopicKnowledgePackage, package_id)
        package.status = "PILOT_APPROVED"; package.approved_by = actor.id; package.approved_at = now
    _audit(db, actor, "knowledge_package.pilot_bulk_approve", "course", course_id,
        f"Pilot approved {len(preview['expected_package_ids'])} knowledge packages",
        package_ids=preview["expected_package_ids"], reason=payload.reason,
        governance="CONTROLLED_PILOT_NOT_INSTITUTIONAL_APPROVAL")
    db.commit()
    return {"approved_count": len(preview["expected_package_ids"]), "status": "PILOT_APPROVED",
        "package_ids": preview["expected_package_ids"], "institutional_approval": False}


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


def external_import_template(db, actor, course_id):
    course = require_manage_course(db, actor, course_id)
    subjects = []
    for subject in db.query(models.Subject).filter_by(course_id=course_id).order_by(models.Subject.sequence, models.Subject.id):
        units = []
        for unit in db.query(models.Unit).filter_by(subject_id=subject.id).order_by(models.Unit.sequence, models.Unit.id):
            topics = []
            for topic in db.query(models.Topic).filter_by(subject_id=subject.id, unit_id=unit.id).order_by(models.Topic.sequence, models.Topic.id):
                subtopics = [{"subtopic_id": row.id, "name": row.name} for row in db.query(models.Subtopic).filter_by(
                    topic_id=topic.id).order_by(models.Subtopic.sequence, models.Subtopic.id)]
                topics.append({"topic_id": topic.id, "name": topic.name, "subtopics": subtopics})
            units.append({"unit_id": unit.id, "name": unit.name, "topics": topics})
        subjects.append({"subject_id": subject.id, "name": subject.name, "units": units})
    return {"schema_version": "SYS-KP-1.0", "course": {"course_id": course.id, "title": course.title,
        "programme_code": course.programme_code}, "syllabus_reference": subjects,
        "import_name": f"{course.programme_code or course.id} external knowledge import",
        "source": {"source_code": "REPLACE-WITH-UNIQUE-CODE", "title": "Authoritative source title",
            "source_type": "TEXTBOOK", "issuing_authority": "Issuing authority", "canonical_url": None,
            "rights_classification": "REFERENCE_ONLY", "content_text": "Paste the source material used to prepare these packages.",
            "verification_statement": "I verified this source and confirm that the imported content is grounded in it."},
        "packages": [{"topic_id": 0, "language": "en-IN", "objectives": ["Replace with a measurable objective"],
            "prerequisites": [], "concepts": [{"name": "Concept", "explanation": "Detailed explanation"}],
            "definitions": [], "formulas": [], "verified_facts": [], "worked_examples": [],
            "misconceptions": [], "exam_relevance": {},
            "subtopic_coverage": [{"subtopic_id": 0, "coverage": "Explain how the package covers this subtopic"}]}]}


def preview_external_import(db, actor, course_id, payload):
    require_manage_course(db, actor, course_id)
    raw = payload.model_dump(exclude={"preview_hash", "confirmation"})
    errors, warnings, mapped, seen = [], [], [], set()
    source_code = payload.source.source_code.strip().upper()
    existing_source = db.query(models.AcademicSource).filter_by(course_id=course_id, source_code=source_code).first()
    if existing_source:
        errors.append(f"Source code {source_code} already exists in this course")
    for index, item in enumerate(payload.packages, 1):
        if item.topic_id in seen:
            errors.append(f"Package {index}: topic {item.topic_id} occurs more than once")
            continue
        seen.add(item.topic_id)
        topic = db.get(models.Topic, item.topic_id)
        if not topic or not topic.subject or topic.subject.course_id != course_id:
            errors.append(f"Package {index}: topic {item.topic_id} does not belong to this course")
            continue
        valid_subtopics = {row.id for row in db.query(models.Subtopic).filter_by(topic_id=topic.id)}
        requested = {entry.get("subtopic_id") for entry in item.subtopic_coverage if entry.get("subtopic_id")}
        invalid = sorted(requested - valid_subtopics)
        if invalid: errors.append(f"Package {index}: subtopics {invalid} do not belong to topic {topic.id}")
        if valid_subtopics - requested:
            warnings.append(f"{topic.name}: {len(valid_subtopics - requested)} syllabus subtopics are not covered")
        existing = db.query(models.TopicKnowledgePackage).filter_by(topic_id=topic.id, language=item.language).first()
        mapped.append({"topic_id": topic.id, "topic_name": topic.name, "subject_id": topic.subject_id,
            "subject_name": topic.subject.name, "subtopics_total": len(valid_subtopics),
            "subtopics_covered": len(requested & valid_subtopics), "result": "NEW_REVISION" if existing else "NEW_PACKAGE",
            "next_revision": (existing.current_revision + 1) if existing else 1})
    return {"valid": not errors, "preview_hash": _hash(raw), "errors": errors, "warnings": warnings,
        "package_count": len(payload.packages), "mapped_packages": mapped,
        "source": {"source_code": source_code, "title": payload.source.title}}


def commit_external_import(db, actor, course_id, payload):
    if (actor.role or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(403, "Administrator import approval is required")
    preview = preview_external_import(db, actor, course_id, payload)
    if payload.preview_hash != preview["preview_hash"]:
        raise HTTPException(409, "The import file changed after preview; preview it again")
    if not preview["valid"]:
        raise HTTPException(422, {"message": "External package validation failed", "errors": preview["errors"]})
    now = datetime.now(timezone.utc); source_data = payload.source
    source = models.AcademicSource(course_id=course_id, source_code=source_data.source_code.strip().upper(),
        title=source_data.title.strip(), source_type=source_data.source_type,
        issuing_authority=source_data.issuing_authority, canonical_url=source_data.canonical_url,
        rights_classification=source_data.rights_classification, verification_status="VERIFIED",
        current_revision=1, created_by=actor.id, verified_by=actor.id, verified_at=now)
    db.add(source); db.flush()
    source_revision = models.AcademicSourceRevision(source_id=source.id, revision=1,
        content_text=source_data.content_text.strip(), content_hash=_hash(source_data.content_text.strip()),
        notes=source_data.verification_statement, created_by=actor.id)
    db.add(source_revision); db.flush()
    imported = []
    for item in payload.packages:
        package = db.query(models.TopicKnowledgePackage).filter_by(topic_id=item.topic_id, language=item.language).first()
        if not package:
            package = models.TopicKnowledgePackage(topic_id=item.topic_id, language=item.language,
                status="DRAFT", current_revision=0, created_by=actor.id); db.add(package); db.flush()
        package.current_revision += 1; package.status = "DRAFT"; package.approved_by = None; package.approved_at = None
        content = item.model_dump(); content["source_revision_ids"] = [source_revision.id]
        revision = models.TopicKnowledgeRevision(package_id=package.id, revision=package.current_revision,
            content_hash=_hash(content), created_by=actor.id, **{key: value for key, value in content.items()
                if key not in {"topic_id", "language"}})
        db.add(revision); imported.append({"topic_id": item.topic_id, "package_id": package.id,
            "revision": package.current_revision, "status": package.status})
    _audit(db, actor, "knowledge_import.commit", "course", course_id,
        f"Imported {len(imported)} external knowledge packages", import_name=payload.import_name,
        source_id=source.id, preview_hash=payload.preview_hash, confirmation=payload.confirmation)
    db.commit()
    return {"imported": len(imported), "source_id": source.id, "source_revision_id": source_revision.id,
        "packages": imported, "warnings": preview["warnings"]}
