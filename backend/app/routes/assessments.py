"""
Assessment Routes for SYS AI Lecturer System
--------------------------------------------
Handles:
 - Create new assessments linked to courses
 - Retrieve all assessments or by ID
 - Update assessment details
 - Delete assessments

Authorization:
 - Read: any authenticated user (student, faculty, admin)
 - Write: faculty or admin
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, database
from app.routes.auth import get_current_user, require_roles

router = APIRouter(prefix="/assessments", tags=["Assessments"])

_staff = require_roles("admin", "faculty")

# =========================
# Create Assessment
# =========================
@router.post("/", response_model=schemas.AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    assessment: schemas.AssessmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    # Ensure course exists
    course = db.query(models.Course).filter(models.Course.id == assessment.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_assessment = models.Assessment(
        title=assessment.title,
        course_id=assessment.course_id,
        due_date=assessment.due_date,
        created_by=current_user.id,
    )
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    return new_assessment


# =========================
# Get All Assessments
# =========================
@router.get("/", response_model=List[schemas.AssessmentOut])
def get_assessments(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    assessments = db.query(models.Assessment).all()
    return assessments


# =========================
# Get Assessment by ID
# =========================
@router.get("/{assessment_id}", response_model=schemas.AssessmentOut)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


# =========================
# Update Assessment
# =========================
@router.put("/{assessment_id}", response_model=schemas.AssessmentOut)
def update_assessment(
    assessment_id: int,
    updated_assessment: schemas.AssessmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Ensure course exists
    course = db.query(models.Course).filter(models.Course.id == updated_assessment.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assessment.title = updated_assessment.title
    assessment.course_id = updated_assessment.course_id
    assessment.due_date = updated_assessment.due_date

    db.commit()
    db.refresh(assessment)
    return assessment


# =========================
# Delete Assessment
# =========================
@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    db.delete(assessment)
    db.commit()
    return None
