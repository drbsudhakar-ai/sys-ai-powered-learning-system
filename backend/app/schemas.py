"""
Pydantic Schemas for SYS AI Lecturer System
"""

from pydantic import BaseModel, EmailStr, Field, SecretStr, StringConstraints
from typing import Optional, List, Any, Dict, Literal, Annotated
from datetime import datetime

UserRole = Literal["super_admin", "admin", "faculty", "student"]
ProvisionableRole = Literal["student", "faculty"]
CleanName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

# =========================
# User Schemas
# =========================
class UserBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    role: UserRole = "student"
    roll_number: Optional[str] = None

class UserCreate(BaseModel):
    name: CleanName
    email: EmailStr
    role: ProvisionableRole
    roll_number: Optional[str] = Field(None, max_length=50)
    employee_code: Optional[str] = Field(None, max_length=50)
    mobile_number: Optional[str] = Field(None, min_length=8, max_length=20)
    password: SecretStr
    photo: Optional[str] = None

    model_config = {"extra": "forbid"}


class UserOut(BaseModel):
    id: int
    name: str
    email: Optional[EmailStr] = None
    institutional_email: Optional[EmailStr] = None
    institutional_mobile: Optional[str] = None
    mobile_number: Optional[str] = None
    email_verified: bool = False
    mobile_verified: bool = False
    mobile_is_personal: bool = True
    role: UserRole
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    college: Optional[str] = None
    academic_program: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    admission_year: Optional[int] = None
    present_year: Optional[int] = None
    academic_status: Optional[str] = None
    employment_status: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True
    account_status: str = "PENDING_ACTIVATION"
    registration_complete: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SelfProfileUpdate(BaseModel):
    """Personal fields a student or faculty member may maintain directly."""

    mobile_number: Optional[str] = Field(None, min_length=8, max_length=20)

    model_config = {"extra": "forbid"}


class AdminUserCreate(BaseModel):
    name: CleanName
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, min_length=8, max_length=20)
    mobile_is_personal: bool = True
    roll_number: Optional[str] = Field(None, max_length=50)
    employee_code: Optional[str] = Field(None, max_length=50)
    photo_url: Optional[str] = None
    college: Optional[str] = Field(None, max_length=160)
    academic_program: Optional[str] = Field(None, max_length=160)
    department: Optional[str] = Field(None, max_length=160)
    designation: Optional[str] = Field(None, max_length=120)
    admission_year: Optional[int] = Field(None, ge=1900, le=2200)
    present_year: Optional[int] = Field(None, ge=1, le=20)
    academic_status: Optional[Literal["ACTIVE", "INACTIVE"]] = None
    employment_status: Optional[Literal["ACTIVE", "INACTIVE"]] = None

    model_config = {"extra": "forbid"}


class AdminUserUpdate(BaseModel):
    name: Optional[CleanName] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, min_length=8, max_length=20)
    mobile_is_personal: Optional[bool] = None
    roll_number: Optional[str] = Field(None, max_length=50)
    employee_code: Optional[str] = Field(None, max_length=50)
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[SecretStr] = None
    college: Optional[str] = Field(None, max_length=160)
    academic_program: Optional[str] = Field(None, max_length=160)
    department: Optional[str] = Field(None, max_length=160)
    designation: Optional[str] = Field(None, max_length=120)
    admission_year: Optional[int] = Field(None, ge=1900, le=2200)
    present_year: Optional[int] = Field(None, ge=1, le=20)
    academic_status: Optional[Literal["ACTIVE", "INACTIVE"]] = None
    employment_status: Optional[Literal["ACTIVE", "INACTIVE"]] = None

    model_config = {"extra": "forbid"}


class MasterProgrammeOut(BaseModel):
    id: int
    title: str


class MasterSubjectOut(BaseModel):
    id: int
    name: str


class AdminMasterRecordOut(BaseModel):
    id: int
    role: ProvisionableRole
    name: str
    photo_url: Optional[str] = None
    roll_number: Optional[str] = None
    employee_code: Optional[str] = None
    email: Optional[EmailStr] = None
    email_verified: bool
    mobile_number: Optional[str] = None
    mobile_masked: Optional[str] = None
    mobile_verified: bool
    registration_status: str
    is_active: bool
    college: Optional[str] = None
    academic_program: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    admission_year: Optional[int] = None
    present_year: Optional[int] = None
    academic_status: Optional[str] = None
    employment_status: Optional[str] = None
    programmes: List[MasterProgrammeOut] = []
    coordinator_assignments: int = 0
    subject_expert_assignments: int = 0
    last_login_at: Optional[datetime] = None
    last_login_available: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdminMasterPageOut(BaseModel):
    items: List[AdminMasterRecordOut]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: Literal[25, 50, 100]


class AdminMasterProfileOut(BaseModel):
    record: AdminMasterRecordOut
    coordinator_courses: List[MasterProgrammeOut] = []
    expert_subjects: List[MasterSubjectOut] = []
    activity: Dict[str, Any] = Field(default_factory=dict)


class AdminBulkStatusRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, max_length=500)
    action: Literal["activate", "deactivate"]

    model_config = {"extra": "forbid"}


class AdminBulkAssignmentRequest(BaseModel):
    faculty_ids: List[int] = Field(..., min_length=1, max_length=500)
    assignment_type: Literal["course_coordinator", "subject_expert"]
    target_id: int = Field(..., ge=1)

    model_config = {"extra": "forbid"}


class AdminBulkResultItem(BaseModel):
    id: int
    success: bool
    error: Optional[str] = None


class AdminBulkResultOut(BaseModel):
    succeeded: int
    failed: int
    results: List[AdminBulkResultItem]


class AdminAuditLogOut(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    summary: str
    created_at: datetime


class AdminMasterRecordCreate(AdminUserCreate):
    role: ProvisionableRole


class AdminMasterBatchCreate(BaseModel):
    records: List[AdminMasterRecordCreate] = Field(..., min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class ActivationStartRequest(BaseModel):
    role: ProvisionableRole
    institutional_id: str = Field(..., min_length=1, max_length=50)
    channel: Literal["email", "mobile"]

    model_config = {"extra": "forbid"}


class ActivationIdentitySummary(BaseModel):
    name: str
    role: ProvisionableRole
    institutional_id: str
    college: Optional[str] = None
    academic_program: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    masked_email: Optional[str] = None


class ChallengeStartResponse(BaseModel):
    challenge_id: str
    message: str
    identity: Optional[ActivationIdentitySummary] = None


class OtpVerifyRequest(BaseModel):
    challenge_id: str = Field(..., min_length=20, max_length=64)
    code: str = Field(..., pattern=r"^\d{6}$")

    model_config = {"extra": "forbid"}


class AuthorizationResponse(BaseModel):
    authorization: str


class ActivationContactRequest(BaseModel):
    action: Literal["send", "verify"]
    ownership_authorization: str = Field(..., min_length=20, max_length=200)
    contact_type: Literal["email", "mobile"]
    contact_value: Optional[str] = Field(None, min_length=3, max_length=255)
    challenge_id: Optional[str] = Field(None, min_length=20, max_length=64)
    code: Optional[str] = Field(None, pattern=r"^\d{6}$")

    model_config = {"extra": "forbid"}


class ActivationCompleteRequest(BaseModel):
    ownership_authorization: str = Field(..., min_length=20, max_length=200)
    email: EmailStr
    email_authorization: str = Field(..., min_length=20, max_length=200)
    mobile_number: Optional[str] = Field(None, min_length=8, max_length=20)
    mobile_authorization: Optional[str] = Field(None, min_length=20, max_length=200)
    password: SecretStr
    confirm_password: SecretStr

    model_config = {"extra": "forbid"}


class AuthMessageResponse(BaseModel):
    message: str


class PasswordResetStartRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=255)
    channel: Literal["email", "mobile"]

    model_config = {"extra": "forbid"}


class PasswordResetCompleteRequest(BaseModel):
    reset_authorization: str = Field(..., min_length=20, max_length=200)
    password: SecretStr
    confirm_password: SecretStr

    model_config = {"extra": "forbid"}


class CourseCoordinatorOut(BaseModel):
    id: int
    faculty_id: int
    faculty_name: str
    faculty_email: Optional[EmailStr] = None
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
    faculty_email: Optional[EmailStr] = None
    subject_id: int
    subject_name: str
    course_id: Optional[int] = None
    course_title: Optional[str] = None
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
    programme_category: Optional[str] = None
    examination_name: Optional[str] = Field(None, max_length=200)
    examination_authority: Optional[str] = Field(None, max_length=200)
    target_purpose: Optional[str] = Field(None, max_length=300)
    programme_code: Optional[str] = Field(None, max_length=80)
    is_active: Optional[bool] = None
    self_enrollment_enabled: bool = False

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    syllabus_url: Optional[str] = Field(None, max_length=255)
    resources_url: Optional[str] = Field(None, max_length=255)
    programme_category: Optional[str] = None
    examination_name: Optional[str] = Field(None, max_length=200)
    examination_authority: Optional[str] = Field(None, max_length=200)
    target_purpose: Optional[str] = Field(None, max_length=300)
    programme_code: Optional[str] = Field(None, max_length=80)
    is_active: Optional[bool] = None
    self_enrollment_enabled: Optional[bool] = None

class CourseOut(CourseBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    programme_category: str
    is_active: bool = False
    publication_status: str = "DRAFT"
    governance_mode: str = "INSTITUTIONAL"
    submitted_for_review_at: Optional[datetime] = None
    submitted_for_review_by: Optional[int] = None
    published_at: Optional[datetime] = None
    published_by: Optional[int] = None
    archived_at: Optional[datetime] = None
    archived_by: Optional[int] = None
    course_coordinators: List[CourseCoordinatorOut] = []
    subject_count: int = 0
    unit_count: int = 0
    topic_count: int = 0
    subtopic_count: int = 0
    student_count: int = 0
    subject_expert_count: int = 0
    syllabus_configuration: Optional[dict] = None
    assessment_count: int = 0
    learning_session_count: int = 0
    question_count: int = 0

    class Config:
        from_attributes = True


class EnrollmentCohortRequest(BaseModel):
    academic_program: Optional[str] = Field(None, max_length=160)
    present_year: Optional[int] = Field(None, ge=1, le=20)
    student_ids: List[int] = Field(default_factory=list, max_length=500)

    model_config = {"extra": "forbid"}


class EnrollmentBulkRequest(EnrollmentCohortRequest):
    reenroll_existing: bool = False
    reason: Optional[str] = Field(None, max_length=255)


class EnrollmentStatusRequest(BaseModel):
    status: Literal["PENDING_ACTIVATION", "ACTIVE", "COMPLETED", "WITHDRAWN", "SUSPENDED"]
    reason: Optional[str] = Field(None, max_length=255)

    model_config = {"extra": "forbid"}


class CoursePublishRequest(BaseModel):
    activate_pending: bool = False
    expected_pending_count: Optional[int] = Field(None, ge=0)

    model_config = {"extra": "forbid"}


class PilotPublishRequest(BaseModel):
    course_code: str = Field(..., min_length=1, max_length=80)
    reason: str = Field(..., min_length=10, max_length=1000)
    activate_pending: bool = False
    expected_pending_count: Optional[int] = Field(None, ge=0)

    model_config = {"extra": "forbid"}


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
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    max_attempts: Optional[int] = Field(1, ge=1)

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
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    max_attempts: Optional[int] = Field(None, ge=1)
    answer_key_released: Optional[bool] = None

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
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    max_attempts: Optional[int] = 1
    answer_key_released: Optional[bool] = False
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
    unit_id: Optional[int] = None

class UnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    subject_id: int
    sequence: int = Field(1, ge=1)

class UnitOut(UnitCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SyllabusImportRow(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    unit: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=200)
    subtopic: Optional[str] = Field(None, max_length=200)
    subject_description: Optional[str] = Field(None, max_length=500)
    unit_description: Optional[str] = Field(None, max_length=500)
    topic_description: Optional[str] = Field(None, max_length=500)
    subtopic_description: Optional[str] = Field(None, max_length=500)
    unit_sequence: int = Field(1, ge=1)

class SyllabusImportRequest(BaseModel):
    rows: List[SyllabusImportRow] = Field(..., min_length=1, max_length=5000)

class SyllabusItemUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    sequence: Optional[int] = Field(None, ge=1)

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
    question_type: str = "SINGLE_MCQ"
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


class QuestionBankCreate(BaseModel):
    stem: Optional[str] = None
    question_text: Optional[str] = None
    question_type: str = "SINGLE_MCQ"
    difficulty: str = "MEDIUM"
    status: str = "DRAFT"
    course_id: int
    subject_id: int
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    marks: Optional[float] = 1.0
    negative_marks: Optional[float] = 0.0
    source: Optional[str] = None
    source_year: Optional[int] = None
    exam_name: Optional[str] = None
    concept_tags: Optional[List[str]] = None
    learning_objective: Optional[str] = None
    shortcut: Optional[str] = None
    alternative_solution: Optional[str] = None
    common_traps: Optional[str] = None
    estimated_time_seconds: Optional[int] = None
    quality_score: Optional[float] = None
    novelty_class: Optional[str] = "NOVEL"


class QuestionBankUpdate(BaseModel):
    stem: Optional[str] = None
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    status: Optional[str] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    marks: Optional[float] = None
    negative_marks: Optional[float] = None
    source: Optional[str] = None
    source_year: Optional[int] = None
    exam_name: Optional[str] = None
    concept_tags: Optional[List[str]] = None
    learning_objective: Optional[str] = None
    shortcut: Optional[str] = None
    alternative_solution: Optional[str] = None
    common_traps: Optional[str] = None
    estimated_time_seconds: Optional[int] = None
    quality_score: Optional[float] = None
    novelty_class: Optional[str] = None


class QuestionBankOut(BaseModel):
    id: int
    stem: str
    question_text: Optional[str] = None
    question_type: str
    difficulty: str
    status: str
    course_id: int
    subject_id: int
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    marks: Optional[float] = None
    negative_marks: Optional[float] = None
    source: Optional[str] = None
    source_year: Optional[int] = None
    exam_name: Optional[str] = None
    concept_tags: Optional[List[str]] = None
    learning_objective: Optional[str] = None
    shortcut: Optional[str] = None
    alternative_solution: Optional[str] = None
    common_traps: Optional[str] = None
    estimated_time_seconds: Optional[int] = None
    quality_score: Optional[float] = None
    novelty_class: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SimilarityCheckIn(BaseModel):
    course_id: int
    text: str


class HistoricalQuestionIn(BaseModel):
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    question_text: str
    question_type: Optional[str] = None
    marks: Optional[float] = None
    difficulty: Optional[str] = None
    concept_tags: Optional[List[str]] = None
    linked_question_id: Optional[int] = None
    similarity_class: Optional[str] = "CONCEPT_VARIANT"


class HistoricalPaperCreate(BaseModel):
    exam_name: str
    exam_year: int
    course_id: int
    exam_type: Optional[str] = None
    source: Optional[str] = None
    questions: Optional[List[HistoricalQuestionIn]] = []


class HistoricalPaperOut(BaseModel):
    id: int
    exam_name: str
    exam_year: int
    course_id: int
    exam_type: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HistoricalQuestionOut(HistoricalQuestionIn):
    id: int
    paper_id: Optional[int] = None
    fingerprint: Optional[str] = None

    class Config:
        from_attributes = True


class HistoricalPaperDetailOut(HistoricalPaperOut):
    questions: List[HistoricalQuestionOut] = []


class SubjectWeightItem(BaseModel):
    subject_id: int
    weight_percent: float


class SubjectWeightageBulk(BaseModel):
    course_id: int
    items: List[SubjectWeightItem]


class TopicWeightItem(BaseModel):
    topic_id: int
    weight_percent: float
    syllabus_importance: Optional[float] = 0.5


class TopicWeightageBulk(BaseModel):
    subject_id: int
    items: List[TopicWeightItem]


class AcademicWeightageItem(BaseModel):
    item_id: int = Field(..., ge=1)
    weight_percent: float = Field(..., ge=0, le=100, allow_inf_nan=False)


class AcademicWeightageGroupUpdate(BaseModel):
    level: Literal["subject", "unit", "topic", "subtopic"]
    parent_id: int = Field(..., ge=1)
    items: List[AcademicWeightageItem] = Field(..., min_length=1, max_length=1000)


class WeightageGovernanceAction(BaseModel):
    action: Literal["recommend", "approve", "return"]
    version: int = Field(..., ge=0)
    comment: str = Field(..., min_length=1, max_length=2000)


class CoordinatorReadinessAction(BaseModel):
    action: Literal["confirm", "reopen"]
    comment: str = Field(..., min_length=1, max_length=2000)


class BulkSubjectApprovalRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)


class PilotGovernanceRequest(BaseModel):
    action: Literal["enable", "disable"]
    course_code: str = Field(..., min_length=1, max_length=80)
    reason: str = Field(..., min_length=10, max_length=1000)


class PilotPrepareSubjectsRequest(BaseModel):
    course_code: str = Field(..., min_length=1, max_length=80)
    reason: str = Field(..., min_length=10, max_length=1000)
    expected_subject_keys: List[str] = Field(..., min_length=1, max_length=100)


class DraftAcademicWeightageItem(BaseModel):
    item_key: str = Field(..., min_length=1, max_length=90)
    weight_percent: float = Field(..., ge=0, le=100, allow_inf_nan=False)


class DraftAcademicWeightageGroupUpdate(BaseModel):
    level: Literal["subject", "unit", "topic", "subtopic"]
    parent_key: str = Field(..., min_length=1, max_length=90)
    items: List[DraftAcademicWeightageItem] = Field(..., min_length=1, max_length=1000)


class PriorityWeightsIn(BaseModel):
    w_historical_weightage: float = 0.25
    w_historical_frequency: float = 0.25
    w_concept_frequency: float = 0.15
    w_recent_trend: float = 0.15
    w_syllabus_importance: float = 0.10
    w_exam_pattern: float = 0.10


class SelectionRequest(BaseModel):
    course_id: int
    total_questions: int = Field(..., gt=0)
    subject_distribution: Optional[Dict[int, int]] = None
    topic_ids: Optional[List[int]] = None
    difficulty_distribution: Optional[Dict[str, int]] = None
    question_types: Optional[List[str]] = None
    reuse_policy: Optional[str] = "MIXED"
    reuse_mix: Optional[Dict[str, float]] = None
    evidence_based: Optional[bool] = True


class AttemptResponseIn(BaseModel):
    assessment_question_id: int
    selected_answer: Optional[str] = None
    marked_for_review: Optional[bool] = None
    clear: Optional[bool] = False
    time_spent_delta: Optional[float] = 0

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
    source_module: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    link_path: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationPreferenceIn(BaseModel):
    category: str
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None


# =========================
# Learning Sessions (P0-013.1 domain schemas)
# =========================
class LearningSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    mode: str
    course_id: int
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    facilitator_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    primary_student_id: Optional[int] = None


class LearningSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class LearningSessionStatusChange(BaseModel):
    status: str


class LearningParticipantIn(BaseModel):
    user_id: int
    role: str = "STUDENT"


class LearningParticipantStatusChange(BaseModel):
    status: str


class LearningObjectiveIn(BaseModel):
    statement: str = Field(..., min_length=1)
    sequence: Optional[int] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    concept_tag: Optional[str] = None


class LearningActivityIn(BaseModel):
    activity_type: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sequence: Optional[int] = None
    scope: str = "COMMON"
    participant_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None
    assessment_id: Optional[int] = None


class LearningActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    sequence: Optional[int] = None
    status: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class LearningEvidenceIn(BaseModel):
    event_type: str
    user_id: Optional[int] = None
    participant_id: Optional[int] = None
    activity_id: Optional[int] = None
    objective_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None


class LearningParticipantOut(BaseModel):
    id: int
    user_id: int
    role: str
    status: str
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LearningObjectiveOut(BaseModel):
    id: int
    statement: str
    sequence: int
    status: str
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    concept_tag: Optional[str] = None

    class Config:
        from_attributes = True


class LearningActivityOut(BaseModel):
    id: int
    activity_type: str
    title: str
    description: Optional[str] = None
    sequence: int
    scope: str
    participant_id: Optional[int] = None
    status: str
    assessment_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class LearningEvidenceOut(BaseModel):
    id: int
    session_id: int
    user_id: Optional[int] = None
    participant_id: Optional[int] = None
    activity_id: Optional[int] = None
    objective_id: Optional[int] = None
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LearningSessionOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    mode: str
    status: str
    course_id: int
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    facilitator_id: Optional[int] = None
    created_by: int
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    outcome_summary: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    participants: List[LearningParticipantOut] = []
    objectives: List[LearningObjectiveOut] = []
    activities: List[LearningActivityOut] = []

    class Config:
        from_attributes = True


class LearningParticipantProgressOut(BaseModel):
    participant_id: int
    user_id: int
    role: str
    participant_status: str
    progress_status: str
    assigned_activities: int
    completed_activities: int
    percent_complete: float
    session_status: str
    note: Optional[str] = None


class LearningSessionProgressOut(BaseModel):
    session_id: int
    mode: str
    session_status: str
    participants: List[LearningParticipantProgressOut] = []


# P0-014 Remedial
class RemedialStatusChange(BaseModel):
    status: str


class RemedialIndividualCreate(BaseModel):
    course_id: int
    learning_gap_id: int


class RemedialInterventionUpdate(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None
    reassessment_required: Optional[bool] = None
    reassessment_completed: Optional[bool] = None


# P0-013.4 Digital classroom / AI Lecturer
class LectureStepControlIn(BaseModel):
    action: str
    step_index: Optional[int] = None


class LecturePlaybackControlIn(BaseModel):
    action: str


class LectureInteractIn(BaseModel):
    intent: str
    message: Optional[str] = Field(default=None, max_length=2000)
    answer: Optional[str] = Field(default=None, max_length=2000)


class LectureStateOut(BaseModel):
    syllabus_review_required: bool = False
    visited_step_indices: List[int] = Field(default_factory=list)
    can_complete: bool = False
    lesson_completed: bool = False
    can_manage_classroom: bool = False
    recap: str = ""
    session_id: int
    activity_id: int
    title: str
    mode: str
    session_status: str
    course_id: int
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    subtopic_id: Optional[int] = None
    course_title: Optional[str] = None
    subject_name: Optional[str] = None
    topic_name: Optional[str] = None
    subtopic_name: Optional[str] = None
    objectives: List[Dict[str, Any]] = []
    teaching_plan: Dict[str, Any]
    current_step_index: int
    current_step: Optional[Dict[str, Any]] = None
    lecture_status: str
    playback_rate: float = 1.0
    step_count: int
    interactions_available: List[str] = []
    controls: Dict[str, Any] = {}
    participant_progress: Optional[Dict[str, Any]] = None


# P0-015 Mastery
class MasteryPolicyUpdate(BaseModel):
    course_id: Optional[int] = None
    mastery_threshold: Optional[float] = None
    practice_threshold: Optional[float] = None
    reassessment_threshold: Optional[float] = None
    min_reassessment_questions: Optional[int] = None
    regression_drop_points: Optional[float] = None


class MasteryTopicAction(BaseModel):
    course_id: int
    topic_id: int
    student_id: Optional[int] = None


class MasteryDeclareReady(BaseModel):
    course_id: int
    topic_id: int
    student_id: Optional[int] = None
    remediation_source: Optional[str] = "SELF_STUDY"


# P0-017 Learning Journey
class LearningActionChoose(BaseModel):
    choice_action_id: Optional[int] = None


class FacultyJourneyRecommend(BaseModel):
    course_id: int
    action_type: str
    topic_id: Optional[int] = None
    reason: Optional[str] = None


class TopicPrerequisiteCreate(BaseModel):
    prerequisite_topic_id: int


class SubjectTopicChoose(BaseModel):
    topic_id: int


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


# P036 Professor-grade academic content foundation
AcademicSourceStatus = Literal["DRAFT", "VERIFIED", "REJECTED", "SUPERSEDED"]
KnowledgePackageStatus = Literal["DRAFT", "SOURCE_REVIEW", "EXPERT_VERIFIED", "APPROVED", "CHANGES_REQUESTED", "SUPERSEDED"]
ProfessorProfileStatus = Literal["DRAFT", "APPROVED", "SUPERSEDED"]


class AcademicSourceCreate(BaseModel):
    course_id: int
    subject_id: Optional[int] = None
    source_code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    source_type: Literal["OFFICIAL_SYLLABUS", "GOVERNMENT", "TEXTBOOK", "FACULTY_NOTE", "JOURNAL", "WEB_REFERENCE", "OTHER"]
    issuing_authority: Optional[str] = Field(None, max_length=240)
    publication_date: Optional[datetime] = None
    canonical_url: Optional[str] = Field(None, max_length=1000)
    rights_classification: Literal["REFERENCE_ONLY", "LICENSED", "OPEN", "PUBLIC_DOMAIN", "INSTITUTION_OWNED"] = "REFERENCE_ONLY"
    content_text: str = Field(min_length=1, max_length=200000)
    revision_notes: Optional[str] = Field(None, max_length=1000)
    model_config = {"extra": "forbid"}


class AcademicSourceDecision(BaseModel):
    action: Literal["VERIFY", "REJECT"]
    comment: str = Field(min_length=5, max_length=1000)
    model_config = {"extra": "forbid"}


class KnowledgePackageRevisionCreate(BaseModel):
    topic_id: int
    language: str = Field(default="en-IN", min_length=2, max_length=16)
    objectives: List[str] = Field(min_length=1, max_length=20)
    prerequisites: List[str] = Field(default_factory=list, max_length=20)
    concepts: List[Dict[str, Any]] = Field(min_length=1, max_length=50)
    definitions: List[Dict[str, Any]] = Field(default_factory=list, max_length=50)
    formulas: List[Dict[str, Any]] = Field(default_factory=list, max_length=50)
    verified_facts: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    worked_examples: List[Dict[str, Any]] = Field(default_factory=list, max_length=30)
    misconceptions: List[Dict[str, Any]] = Field(default_factory=list, max_length=30)
    exam_relevance: Dict[str, Any] = Field(default_factory=dict)
    subtopic_coverage: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    source_revision_ids: List[int] = Field(min_length=1, max_length=100)
    model_config = {"extra": "forbid"}


class AcademicWorkflowDecision(BaseModel):
    action: Literal["SUBMIT", "EXPERT_VERIFY", "APPROVE", "REQUEST_CHANGES", "SUPERSEDE"]
    comment: str = Field(min_length=5, max_length=1000)
    model_config = {"extra": "forbid"}


class ProfessorProfileUpsert(BaseModel):
    subject_id: int
    language: str = Field(default="en-IN", min_length=2, max_length=16)
    teaching_strategy: Dict[str, Any]
    required_stage_types: List[str] = Field(min_length=5, max_length=30)
    example_rules: List[str] = Field(default_factory=list, max_length=30)
    narration_rules: List[str] = Field(min_length=1, max_length=30)
    visual_rules: List[str] = Field(default_factory=list, max_length=30)
    assessment_rules: List[str] = Field(default_factory=list, max_length=30)
    accuracy_constraints: List[str] = Field(min_length=1, max_length=30)
    model_config = {"extra": "forbid"}


class TopicReviewerAssignmentCreate(BaseModel):
    topic_id: int
    faculty_id: int
    model_config = {"extra": "forbid"}
