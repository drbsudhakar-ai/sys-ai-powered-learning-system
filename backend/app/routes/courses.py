"""
Course Routes for SYS AI Lecturer System
----------------------------------------
A SYS Course is a goal-oriented preparation / learning programme.

Authorization:
 - Read catalog: any authenticated user
 - Write: faculty or admin
 - Self-enroll: student
 - My programmes: authenticated user (own enrollments only)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.constants import (
    DEFAULT_PROGRAMME_CATEGORY,
    PROGRAMME_CATEGORIES,
    PROGRAMME_CODE_ENGLISH_COMMUNICATION,
)
from app.routes.auth import get_current_user, require_roles
from app.services import course_learning

router = APIRouter(prefix="/courses", tags=["Courses"])

_staff = require_roles("admin", "faculty")


def _normalize_category(value: Optional[str], *, required: bool = False) -> Optional[str]:
    if value is None or value == "":
        return DEFAULT_PROGRAMME_CATEGORY if required else None
    cat = str(value).strip().upper()
    if cat not in PROGRAMME_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid programme_category. Allowed: {', '.join(PROGRAMME_CATEGORIES)}",
        )
    return cat


def _normalize_code(value: Optional[str]) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip().upper()


def _validate_programme(category: str, programme_code: Optional[str]) -> None:
    if programme_code == PROGRAMME_CODE_ENGLISH_COMMUNICATION and category != "INDEPENDENT_LEARNING":
        raise HTTPException(
            status_code=422,
            detail="English Communication must use programme_category INDEPENDENT_LEARNING",
        )


def _ensure_unique_course_code(db: Session, code: Optional[str], *, exclude_id: Optional[int] = None) -> None:
    if not code:
        return
    query = db.query(models.Course.id).filter(func.upper(models.Course.programme_code) == code)
    if exclude_id is not None:
        query = query.filter(models.Course.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="A course with this course code already exists")


def _course_out(course: models.Course, db: Session, actor=None) -> schemas.CourseOut:
    coords = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.course_id == course.id)
        .all()
    )
    coordinators = []
    for row in coords:
        faculty = db.query(models.User).filter(models.User.id == row.faculty_id).first()
        coordinators.append(
            schemas.CourseCoordinatorOut(
                id=row.id,
                faculty_id=row.faculty_id,
                faculty_name=faculty.name if faculty else "",
                faculty_email=(faculty.email or faculty.institutional_email) if faculty else None,
                course_id=row.course_id,
                course_title=course.title,
                assigned_at=row.assigned_at,
            )
        )
    result = schemas.CourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        syllabus_url=course.syllabus_url,
        resources_url=course.resources_url,
        programme_category=course.programme_category or DEFAULT_PROGRAMME_CATEGORY,
        examination_name=course.examination_name,
        examination_authority=course.examination_authority,
        target_purpose=course.target_purpose,
        programme_code=course.programme_code,
        is_active=bool(course.is_active),
        publication_status=course.publication_status or ("PUBLISHED" if course.is_active else "DRAFT"),
        governance_mode=course.governance_mode or "INSTITUTIONAL",
        self_enrollment_enabled=bool(course.self_enrollment_enabled),
        submitted_for_review_at=course.submitted_for_review_at,
        submitted_for_review_by=course.submitted_for_review_by,
        published_at=course.published_at,
        published_by=course.published_by,
        archived_at=course.archived_at,
        archived_by=course.archived_by,
        created_by=course.created_by,
        created_at=course.created_at,
        course_coordinators=coordinators,
        subject_count=db.query(models.Subject.id).filter(models.Subject.course_id == course.id).count(),
        unit_count=db.query(models.Unit.id).join(models.Subject, models.Subject.id == models.Unit.subject_id).filter(models.Subject.course_id == course.id).count(),
        topic_count=db.query(models.Topic.id).join(models.Subject, models.Subject.id == models.Topic.subject_id).filter(models.Subject.course_id == course.id).count(),
        subtopic_count=db.query(models.Subtopic.id).join(models.Topic, models.Topic.id == models.Subtopic.topic_id).join(models.Subject, models.Subject.id == models.Topic.subject_id).filter(models.Subject.course_id == course.id).count(),
        student_count=db.query(models.StudentCourseEnrollment.id).filter(models.StudentCourseEnrollment.course_id == course.id, models.StudentCourseEnrollment.status == "ACTIVE").count(),
        subject_expert_count=db.query(models.SubjectExpertAssignment.id).join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id).filter(models.Subject.course_id == course.id).count(),
        assessment_count=db.query(models.Assessment.id).filter(models.Assessment.course_id == course.id).count(),
        learning_session_count=db.query(models.LearningSession.id).filter(models.LearningSession.course_id == course.id).count(),
        question_count=db.query(models.Question.id).filter(models.Question.course_id == course.id).count(),
    )
    from app.services.syllabus_review import manager
    if actor is not None and manager(db, actor, course.id):
        from app.services.syllabus_configuration import configuration
        configured = configuration(db, course)
        for level in ('subject', 'unit', 'topic', 'subtopic'):
            setattr(result, f'{level}_count', configured[f'{level}_count'])
        result.subject_expert_count = len(configured['experts'])
        result.syllabus_configuration = configured
    return result


def _universal_support_payload() -> dict:
    """Existing universal student services — not a Motivation Agent."""
    return {
        "available": True,
        "requires_course_enrollment": False,
        "entry_points": ["/programs", "/notifications"],
        "note": "Motivation & Support agent is not implemented in this release. Inbox and programme pages remain available to any authorized student.",
    }


@router.post("/", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    course: schemas.CourseCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    category = _normalize_category(course.programme_category, required=True)
    code = _normalize_code(course.programme_code)
    _validate_programme(category, code)
    _ensure_unique_course_code(db, code)
    is_active = False
    new_course = models.Course(
        title=course.title,
        description=course.description,
        syllabus_url=course.syllabus_url,
        resources_url=course.resources_url,
        programme_category=category,
        examination_name=course.examination_name,
        examination_authority=course.examination_authority,
        target_purpose=course.target_purpose,
        programme_code=code,
        is_active=is_active,
        publication_status="DRAFT",
        self_enrollment_enabled=course.self_enrollment_enabled,
        created_by=current_user.id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return _course_out(new_course, db)


@router.get("/me")
def my_programmes(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Own programme enrollments. Empty list is valid — enrollment is not required."""
    rows = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.student_id == current_user.id)
        .all()
    )
    enrollments = []
    for row in rows:
        course = db.query(models.Course).filter(models.Course.id == row.course_id).first()
        if not course:
            continue
        from app.services.course_enrollments import has_learning_access
        can_access = has_learning_access(db, current_user.id, course.id)
        # Pending/unavailable assignments reveal identity only, never draft materials.
        item = _course_out(course, db).model_dump() if can_access else {
            "id": course.id, "title": course.title, "programme_code": course.programme_code,
            "publication_status": course.publication_status,
        }
        item["enrollment_status"] = row.status
        item["can_access"] = can_access
        item["lock_reason"] = None if can_access else (
            "Awaiting course publication and administrator activation." if row.status == "PENDING_ACTIVATION"
            else "This enrollment or course is not currently available for learning. Contact your administrator."
        )
        item["learning"] = course_learning.student_learning_summary(db, current_user.id, course.id) if can_access else None
        item["enrolled_at"] = row.enrolled_at.isoformat() if row.enrolled_at else None
        enrollments.append(item)
    return {
        "student_id": current_user.id,
        "enrollments": enrollments,
        "enrollment_required": False,
        "universal_support": _universal_support_payload(),
        "hierarchy_note": "Learning content follows Course → Subject → Unit → Topic → Subtopic.",
    }


@router.get("/", response_model=List[schemas.CourseOut])
def get_courses(
    programme_category: Optional[str] = Query(None),
    programme_code: Optional[str] = Query(None),
    active_only: Optional[bool] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Course)
    if programme_category:
        q = q.filter(models.Course.programme_category == _normalize_category(programme_category, required=True))
    if programme_code:
        q = q.filter(models.Course.programme_code == _normalize_code(programme_code))
    role = (current_user.role or "").lower()
    hide_inactive = role == "student" or bool(active_only)
    if hide_inactive:
        q = q.filter(
            models.Course.is_active.is_(True),
            models.Course.publication_status == "PUBLISHED",
        )
    courses = q.order_by(models.Course.id).all()
    return [_course_out(c, db, current_user) for c in courses]


@router.get("/{course_id}", response_model=schemas.CourseOut)
def get_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    pilot_enrolled = db.query(models.StudentCourseEnrollment.id).filter_by(
        student_id=current_user.id, course_id=course_id, status="ACTIVE").first() if course else None
    student_visible = course and course.is_active and (course.publication_status == "PUBLISHED" or
        course.publication_status == "PILOT_PUBLISHED" and pilot_enrolled)
    if not course or ((current_user.role or "").lower() == "student" and not student_visible):
        raise HTTPException(status_code=404, detail="Course not found")
    return _course_out(course, db, current_user)


@router.post("/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_roles("student")),
):
    """Allow self-enrollment only when an administrator enabled it for the course."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course or not course.is_active or course.publication_status != "PUBLISHED":
        raise HTTPException(status_code=404, detail="Published course not found")
    if not course.self_enrollment_enabled:
        raise HTTPException(status_code=403, detail="Self-enrollment is not enabled for this course")

    existing = (
        db.query(models.StudentCourseEnrollment)
        .filter(
            models.StudentCourseEnrollment.student_id == current_user.id,
            models.StudentCourseEnrollment.course_id == course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You are already enrolled in this course")

    enrollment = models.StudentCourseEnrollment(
        student_id=current_user.id,
        course_id=course_id,
        enrollment_source="SELF",
        enrolled_by=current_user.id,
    )
    db.add(enrollment)
    try:
        db.flush()
        db.add(
            models.AdminAuditLog(
                actor_user_id=current_user.id,
                action="course.student_enrolled",
                target_type="course",
                target_id=course_id,
                summary=f"Student enrolled in {course.title}",
                details={"student_id": current_user.id, "enrollment_id": enrollment.id},
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You are already enrolled in this course")
    db.refresh(enrollment)
    return {
        "id": enrollment.id,
        "student_id": current_user.id,
        "course_id": course_id,
        "enrolled_at": enrollment.enrolled_at,
        "message": "Course enrollment completed successfully.",
    }


@router.get("/{course_id}/workspace")
def course_workspace(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the full syllabus only within the caller's academic scope."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    role = (current_user.role or "").lower()
    allowed_subject_ids = None
    coordinator = False
    if role == "student":
        enrolled = (
            db.query(models.StudentCourseEnrollment.id)
            .filter(
                models.StudentCourseEnrollment.student_id == current_user.id,
                models.StudentCourseEnrollment.course_id == course_id,
                models.StudentCourseEnrollment.status == "ACTIVE",
            )
            .first()
        )
        from app.services.course_enrollments import has_learning_access
        if not enrolled or not course.is_active or course.publication_status not in {"PUBLISHED", "PILOT_PUBLISHED"} or not has_learning_access(db, current_user.id, course_id):
            raise HTTPException(status_code=403, detail="Enrollment in this published course is required")
    elif role == "faculty":
        coordinator_assignment = (
            db.query(models.FacultyCourseAssignment.id)
            .filter(
                models.FacultyCourseAssignment.faculty_id == current_user.id,
                models.FacultyCourseAssignment.course_id == course_id,
            )
            .first()
        )
        expert = (
            db.query(models.SubjectExpertAssignment.id)
            .join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id)
            .filter(
                models.SubjectExpertAssignment.faculty_id == current_user.id,
                models.Subject.course_id == course_id,
            )
            .first()
        )
        coordinator = bool(coordinator_assignment)
        draft_expert = (
            db.query(models.SyllabusSubjectReview.id)
            .join(models.SyllabusReview, models.SyllabusReview.id == models.SyllabusSubjectReview.review_id)
            .filter(
                models.SyllabusSubjectReview.reviewer_id == current_user.id,
                models.SyllabusReview.course_id == course_id,
                models.SyllabusReview.subject_id.is_(None),
                models.SyllabusReview.status.in_(("DRAFT", "CHANGES_REQUESTED")),
            )
            .first()
        )
        if not coordinator and not expert and not draft_expert:
            raise HTTPException(status_code=403, detail="Academic responsibility for this course is required")
        if not coordinator:
            allowed_subject_ids = {
                assignment.subject_id
                for assignment in db.query(models.SubjectExpertAssignment)
                .join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id)
                .filter(
                    models.SubjectExpertAssignment.faculty_id == current_user.id,
                    models.Subject.course_id == course_id,
                )
                .all()
            }
    elif role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    draft_projection = None
    if role == "faculty":
        from app.services.faculty_syllabus_scope import workspace_projection
        draft_projection = workspace_projection(db, course, current_user, coordinator=coordinator)

    subjects = []
    for subject in sorted(course.subjects, key=lambda item: (item.sequence, item.name.lower())):
        if allowed_subject_ids is not None and subject.id not in allowed_subject_ids:
            continue
        experts = [
            {"id": assignment.faculty.id, "name": assignment.faculty.name}
            for assignment in subject.expert_assignments
            if assignment.faculty
        ]
        units = []
        for unit in sorted(subject.units, key=lambda item: (item.sequence, item.name.lower())):
            topics = [
                {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description,
                    "subtopics": [
                        {"id": subtopic.id, "name": subtopic.name, "description": subtopic.description}
                        for subtopic in sorted(topic.subtopics, key=lambda item: (item.sequence, item.name.lower()))
                    ],
                }
                for topic in sorted(unit.topics, key=lambda item: (item.sequence, item.name.lower()))
            ]
            units.append({"id": unit.id, "name": unit.name, "sequence": unit.sequence, "topics": topics})
        subjects.append({"id": subject.id, "name": subject.name, "experts": experts, "units": units})

    from app.services.learning_workspace import enrich_syllabus
    enrich_syllabus(db, course_id, subjects)
    syllabus_status = {"status": "PUBLISHED" if course.publication_status == "PUBLISHED" else "CONFIGURED", "is_draft": False}
    if draft_projection:
        subjects = draft_projection["subjects"]
        syllabus_status = {key: value for key, value in draft_projection.items() if key != "subjects"}
    if role == "student":
        learning = course_learning.student_learning_summary(db, current_user.id, course_id)
    else:
        session_query = db.query(models.LearningSession.id).filter(
            models.LearningSession.course_id == course_id
        )
        if allowed_subject_ids is not None:
            session_query = session_query.filter(
                models.LearningSession.subject_id.in_(allowed_subject_ids)
            )
        learning = {
            "status": "FACULTY_WORKSPACE",
            "message": "Create and manage Common, Individual, or Hybrid learning sessions within your assigned academic scope.",
            "session_count": session_query.count(),
            "topic_sessions": {},
        }

    course_data = _course_out(course, db).model_dump()
    if draft_projection:
        course_data["subject_count"] = draft_projection["subject_count"]
        course_data["unit_count"] = draft_projection["unit_count"]
        course_data["topic_count"] = draft_projection["topic_count"]
    return {
        "course": course_data,
        "role": role,
        "syllabus": subjects,
        "syllabus_status": syllabus_status,
        "learning": learning,
        "assessments": {"count": 0, "message": "No assessments are available yet."},
        "remedial": {"count": 0, "message": "No remedial activities have been assigned."},
        "mastery": {"status": "NOT_STARTED", "message": "Mastery practice has not started yet."},
        "materials": {"count": 0, "message": "No course materials have been published yet."},
    }


@router.post("/{course_id}/learning/topics/{topic_id}/launch")
def launch_topic_learning(
    course_id: int,
    topic_id: int,
    subtopic_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_roles("student")),
):
    """Start or resume the caller's authorized individual AI Lecturer lesson."""
    return course_learning.launch_or_resume_topic(
        db,
        current_user,
        course_id=course_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
    )


@router.put("/{course_id}", response_model=schemas.CourseOut)
def update_course(
    course_id: int,
    updated_course: schemas.CourseUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    data = updated_course.model_dump(exclude_unset=True)
    if "is_active" in data and data["is_active"] != course.is_active:
        raise HTTPException(status_code=422, detail="Use the controlled course publication workflow to change catalogue availability")
    if "programme_category" in data:
        data["programme_category"] = _normalize_category(data.get("programme_category"), required=True)
    if "programme_code" in data:
        data["programme_code"] = _normalize_code(data.get("programme_code"))
    next_category = data.get("programme_category") or course.programme_category or DEFAULT_PROGRAMME_CATEGORY
    next_code = data["programme_code"] if "programme_code" in data else course.programme_code
    _validate_programme(next_category, next_code)
    _ensure_unique_course_code(db, next_code, exclude_id=course.id)

    for key, value in data.items():
        setattr(course, key, value)

    db.commit()
    db.refresh(course)
    return _course_out(course, db)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return None
