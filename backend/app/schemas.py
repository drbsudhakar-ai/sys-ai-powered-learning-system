"""
Pydantic Schemas for SYS AI Lecturer System
-------------------------------------------
Defines request and response models for:
 - Users (Auth)
 - Courses
 - Assessments
 - Resources
"""

from pydantic import BaseModel, EmailStr, Field
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
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    photo_url: Optional[str] = None


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class CourseCoordinatorOut(BaseModel):
    id: int
    faculty_id: int
    faculty_name: str
    faculty_email: EmailStr
    course_id: int
    course_title: str
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseCoordinatorCreate(BaseModel):
    faculty_id: int
    course_id: int


class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    course_id: Optional[int] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectOut(SubjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubjectExpertOut(BaseModel):
    id: int
    faculty_id: int
    faculty_name: str
    faculty_email: EmailStr
    subject_id: int
    subject_name: str
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubjectExpertCreate(BaseModel):
    faculty_id: int
    subject_id: int


class FacultyResponsibilitiesOut(BaseModel):
    faculty: UserOut
    course_coordinator_assignments: List[CourseCoordinatorOut] = []
    subject_expert_assignments: List[SubjectExpertOut] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================
# Course Schemas
# =========================
class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    syllabus_url: Optional[str] = Field(None, max_length=255)
    resources_url: Optional[str] = Field(None, max_length=255)

class CourseCreate(CourseBase):
    pass

class CourseOut(CourseBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    course_coordinators: List[CourseCoordinatorOut] = []

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