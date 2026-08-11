"""
Course Routes for SYS AI Lecturer System
----------------------------------------
Handles:
 - Create new courses
 - Retrieve all courses or by ID
 - Update course details
 - Delete courses
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, database

router = APIRouter(prefix="/courses", tags=["Courses"])

# =========================
# Create Course
# =========================
@router.post("/", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(course: schemas.CourseCreate, db: Session = Depends(database.get_db)):
    new_course = models.Course(
        title=course.title,
        description=course.description,
        duration=course.duration,
        category=course.category
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


# =========================
# Get All Courses
# =========================
@router.get("/", response_model=List[schemas.CourseOut])
def get_courses(db: Session = Depends(database.get_db)):
    courses = db.query(models.Course).all()
    return courses


# =========================
# Get Course by ID
# =========================
@router.get("/{course_id}", response_model=schemas.CourseOut)
def get_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# =========================
# Update Course
# =========================
@router.put("/{course_id}", response_model=schemas.CourseOut)
def update_course(course_id: int, updated_course: schemas.CourseCreate, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.title = updated_course.title
    course.description = updated_course.description
    course.duration = updated_course.duration
    course.category = updated_course.category

    db.commit()
    db.refresh(course)
    return course


# =========================
# Delete Course
# =========================
@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return None
