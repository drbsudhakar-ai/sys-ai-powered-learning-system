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
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.constants import (
    DEFAULT_PROGRAMME_CATEGORY,
    PROGRAMME_CATEGORIES,
    PROGRAMME_CODE_ENGLISH_COMMUNICATION,
)
from app.routes.auth import get_current_user, require_roles

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


def _course_out(course: models.Course, db: Session) -> schemas.CourseOut:
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
    return schemas.CourseOut(
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
        is_active=bool(course.is_active) if course.is_active is not None else True,
        created_by=course.created_by,
        created_at=course.created_at,
        course_coordinators=coordinators,
    )


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
    is_active = True if course.is_active is None else bool(course.is_active)
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
        item = _course_out(course, db).model_dump()
        item["enrolled_at"] = row.enrolled_at.isoformat() if row.enrolled_at else None
        enrollments.append(item)
    return {
        "student_id": current_user.id,
        "enrollments": enrollments,
        "enrollment_required": False,
        "universal_support": _universal_support_payload(),
        "hierarchy_note": "Learning content uses existing Course → Subject → Topic (optional Subtopic). No separate Unit table is present.",
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
    hide_inactive = active_only if active_only is not None else (role == "student")
    if hide_inactive:
        q = q.filter(models.Course.is_active.is_(True))
    courses = q.order_by(models.Course.id).all()
    return [_course_out(c, db) for c in courses]


@router.get("/{course_id}", response_model=schemas.CourseOut)
def get_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return _course_out(course, db)


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
    if "programme_category" in data:
        data["programme_category"] = _normalize_category(data.get("programme_category"), required=True)
    if "programme_code" in data:
        data["programme_code"] = _normalize_code(data.get("programme_code"))
    next_category = data.get("programme_category") or course.programme_category or DEFAULT_PROGRAMME_CATEGORY
    next_code = data["programme_code"] if "programme_code" in data else course.programme_code
    _validate_programme(next_category, next_code)

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
