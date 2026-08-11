"""
Resource Routes for SYS AI Lecturer System
------------------------------------------
Handles:
 - Upload new resources linked to courses
 - Retrieve all resources or by ID
 - Update resource details
 - Delete resources
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, database

router = APIRouter(prefix="/resources", tags=["Resources"])

# =========================
# Create Resource
# =========================
@router.post("/", response_model=schemas.ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(resource: schemas.ResourceCreate, db: Session = Depends(database.get_db)):
    # Ensure course exists
    course = db.query(models.Course).filter(models.Course.id == resource.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_resource = models.Resource(
        name=resource.name,
        type=resource.type,
        file_url=resource.file_url,
        status=resource.status,
        course_id=resource.course_id
    )
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)
    return new_resource


# =========================
# Get All Resources
# =========================
@router.get("/", response_model=List[schemas.ResourceOut])
def get_resources(db: Session = Depends(database.get_db)):
    resources = db.query(models.Resource).all()
    return resources


# =========================
# Get Resource by ID
# =========================
@router.get("/{resource_id}", response_model=schemas.ResourceOut)
def get_resource(resource_id: int, db: Session = Depends(database.get_db)):
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


# =========================
# Update Resource
# =========================
@router.put("/{resource_id}", response_model=schemas.ResourceOut)
def update_resource(resource_id: int, updated_resource: schemas.ResourceCreate, db: Session = Depends(database.get_db)):
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Ensure course exists
    course = db.query(models.Course).filter(models.Course.id == updated_resource.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    resource.name = updated_resource.name
    resource.type = updated_resource.type
    resource.file_url = updated_resource.file_url
    resource.status = updated_resource.status
    resource.course_id = updated_resource.course_id

    db.commit()
    db.refresh(resource)
    return resource


# =========================
# Delete Resource
# =========================
@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: int, db: Session = Depends(database.get_db)):
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    db.delete(resource)
    db.commit()
    return None
