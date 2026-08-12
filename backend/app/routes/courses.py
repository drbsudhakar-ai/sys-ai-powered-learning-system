"""
Course Routes for SYS AI Lecturer System
----------------------------------------
Handles:
 - Create new courses
 - Retrieve all courses or by ID
 - Update course details
 - Delete courses

Authorization:
 - Read: any authenticated user (student, faculty, admin)
 - Write: faculty or admin
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, database
from app.routes.auth import get_current_user, require_roles

router = APIRouter(prefix="/courses", tags=["Courses"])

_staff = require_roles("admin", "faculty")


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
                faculty_email=faculty.email if faculty else "unknown@example.com",
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
        created_by=course.created_by,
        created_at=course.created_at,
        course_coordinators=coordinators,
    )

# =========================
# Create Course
# =========================
@router.post("/", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    course: schemas.CourseCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    new_course = models.Course(
        title=course.title,
        description=course.description,
        syllabus_url=course.syllabus_url,
        resources_url=course.resources_url,
        created_by=current_user.id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return _course_out(new_course, db)


# =========================
# Get All Courses
# =========================
@router.get("/", response_model=List[schemas.CourseOut])
def get_courses(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    courses = db.query(models.Course).all()
    return [_course_out(c, db) for c in courses]


# =========================
# Get Course by ID
# =========================
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


# =========================
# Update Course
# =========================
@router.put("/{course_id}", response_model=schemas.CourseOut)
def update_course(
    course_id: int,
    updated_course: schemas.CourseCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.title = updated_course.title
    course.description = updated_course.description
    course.syllabus_url = updated_course.syllabus_url
    course.resources_url = updated_course.resources_url

    db.commit()
    db.refresh(course)
    return _course_out(course, db)


# =========================
# Delete Course
# =========================
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
