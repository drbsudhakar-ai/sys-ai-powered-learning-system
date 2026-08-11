"""
Pydantic Schemas for SYS AI Lecturer System
-------------------------------------------
Defines request and response models for:
 - Users (Auth)
 - Courses
 - Assessments
 - Resources
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# =========================
# User Schemas
# =========================
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "student"  # student/admin
    roll_number: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str   # "student", "admin", "faculty"
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    password: str
    photo: Optional[str] = None

    # ✅ Role-based validation
    @classmethod
    def validate(cls, values):
        role = values.get("role")
        if role == "student" and not values.get("roll_number"):
            raise ValueError("Roll number is mandatory for students.")
        if role in ["admin", "faculty"] and not values.get("employee_code"):
            raise ValueError("Employee code is mandatory for admin/faculty.")
        return values


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================
# Course Schemas
# =========================
class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseOut(CourseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# Assessment Schemas
# =========================
class AssessmentBase(BaseModel):
    title: str

class AssessmentCreate(AssessmentBase):
    course_id: int
    due_date: Optional[datetime] = None

class AssessmentOut(AssessmentBase):
    id: int
    course_id: int
    created_at: datetime
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================
# Resource Schemas
# =========================
class ResourceBase(BaseModel):
    name: str
    type: str  # PDF, Word, Image, Video
    file_url: str
    status: Optional[str] = "Available"

class ResourceCreate(ResourceBase):
    course_id: int

class ResourceOut(ResourceBase):
    id: int
    course_id: int
    upload_date: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str