"""
Pydantic Schemas for SYS AI Lecturer System
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

# =========================
# User Schemas
# =========================
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "student"
    roll_number: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    password: str
    photo: Optional[str] = None

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
# Assessment Schemas (P0-009)
# =========================
class AssessmentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class AssessmentCreate(AssessmentBase):
    course_id: int
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    assessment_type: str = "TOPIC_TEST"
    duration_minutes: Optional[int] = Field(None, gt=0)
    total_questions: Optional[int] = Field(None, gt=0)
    total_marks: Optional[float] = Field(None, gt=0)
    marks_correct: Optional[float] = 1.0
    marks_incorrect: Optional[float] = 0.0
    marks_unanswered: Optional[float] = 0.0
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None

class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    assessment_type: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    total_questions: Optional[int] = Field(None, gt=0)
    total_marks: Optional[float] = Field(None, gt=0)
    marks_correct: Optional[float] = None
    marks_incorrect: Optional[float] = None
    marks_unanswered: Optional[float] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    status: Optional[str] = None

class BlueprintItemIn(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    difficulty: str
    question_count: int = Field(..., gt=0)

class BlueprintItemOut(BlueprintItemIn):
    id: int

    class Config:
        from_attributes = True

class AssessmentQuestionOut(BaseModel):
    id: int
    question_id: int
    sequence: int
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    difficulty: Optional[str] = None
    marks_available: float

    class Config:
        from_attributes = True

class AssessmentVersionOut(BaseModel):
    id: int
    assessment_id: int
    version_number: int
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    total_marks: Optional[float] = None
    category: Optional[str] = None
    assessment_type: Optional[str] = None
    published_at: Optional[datetime] = None
    questions: List[AssessmentQuestionOut] = []

    class Config:
        from_attributes = True

class AssessmentOut(AssessmentBase):
    id: int
    course_id: int
    created_at: datetime
    due_date: Optional[datetime] = None
    created_by: Optional[int] = None
    category: Optional[str] = None
    assessment_type: Optional[str] = None
    status: str = "DRAFT"
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    total_marks: Optional[float] = None
    marks_correct: Optional[float] = None
    marks_incorrect: Optional[float] = None
    marks_unanswered: Optional[float] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    blueprint_items: List[BlueprintItemOut] = []
    versions: List[AssessmentVersionOut] = []

    class Config:
        from_attributes = True

class PublishResult(BaseModel):
    assessment_id: int
    version_id: int
    version_number: int
    question_count: int
    validation_errors: List[str] = []

class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    subject_id: int

class TopicOut(TopicCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SubtopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    topic_id: int

class SubtopicOut(SubtopicCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    stem: str = Field(..., min_length=1)
    question_type: str = "MCQ"
    difficulty: str = "MEDIUM"
    course_id: int
    subject_id: int
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    status: str = "ACTIVE"

class QuestionOut(QuestionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationRecipientCreate(BaseModel):
    name: str
    designation: Optional[str] = None
    email: EmailStr
    recipient_type: str = "CUSTOM_RECIPIENT"
    is_active: bool = True
    event_types: Optional[List[str]] = None
    course_id: Optional[int] = None
    frequency: str = "IMMEDIATE"

class NotificationRecipientUpdate(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[EmailStr] = None
    recipient_type: Optional[str] = None
    is_active: Optional[bool] = None
    event_types: Optional[List[str]] = None
    course_id: Optional[int] = None
    frequency: Optional[str] = None

class NotificationRecipientOut(NotificationRecipientCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationOut(BaseModel):
    id: int
    event: str
    assessment_id: Optional[int] = None
    course_id: Optional[int] = None
    student_id: Optional[int] = None
    recipients: List[str] = []
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PerformanceSheetOut(BaseModel):
    student: Dict[str, Any]
    course: Dict[str, Any]
    topic_assessments: List[Dict[str, Any]] = []
    weekly_tests: List[Dict[str, Any]] = []
    monthly_tests: List[Dict[str, Any]] = []
    grand_tests: List[Dict[str, Any]] = []
    final_grand_tests: List[Dict[str, Any]] = []
    subject_summary: List[Dict[str, Any]] = []
    overall_summary: Dict[str, Any] = {}


# =========================
# Resource Schemas
# =========================
class ResourceBase(BaseModel):
    name: str
    type: str
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
