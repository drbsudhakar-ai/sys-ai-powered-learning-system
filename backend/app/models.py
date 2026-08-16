"""
SQLAlchemy Models
-----------------
SYS AI Lecturer System
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
    Float,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


# =========================
# User Model
# =========================

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "lower(role) <> 'student' OR (roll_number IS NOT NULL AND trim(roll_number) <> '')",
            name="ck_users_student_roll_required",
        ),
        CheckConstraint(
            "lower(role) <> 'faculty' OR (employee_code IS NOT NULL AND trim(employee_code) <> '')",
            name="ck_users_faculty_employee_required",
        ),
        CheckConstraint(
            "roll_number IS NULL OR roll_number = upper(trim(roll_number))",
            name="ck_users_roll_number_normalized",
        ),
        CheckConstraint(
            "employee_code IS NULL OR employee_code = upper(trim(employee_code))",
            name="ck_users_employee_code_normalized",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    institutional_email = Column(String(255), nullable=True)
    institutional_mobile = Column(String(20), nullable=True)
    mobile_number = Column(String(20), unique=True, index=True, nullable=True)
    email_verified = Column(Boolean, nullable=False, server_default="false", default=True)
    mobile_verified = Column(Boolean, nullable=False, server_default="false", default=False)
    mobile_is_personal = Column(Boolean, nullable=False, server_default="true", default=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False)  # super_admin, admin, faculty, student
    roll_number = Column(String(50), index=True, nullable=True)
    employee_code = Column(String(50), index=True, nullable=True)
    college = Column(String(160), nullable=True, index=True)
    department = Column(String(160), nullable=True, index=True)
    designation = Column(String(120), nullable=True, index=True)
    admission_year = Column(Integer, nullable=True, index=True)
    present_year = Column(Integer, nullable=True, index=True)
    academic_status = Column(String(32), nullable=True, index=True)
    employment_status = Column(String(32), nullable=True, index=True)
    photo_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    account_status = Column(
        String(32),
        nullable=False,
        server_default="PENDING_ACTIVATION",
        default="ACTIVE",
    )
    session_version = Column(Integer, nullable=False, server_default="1", default=1)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    enrollments = relationship("StudentCourseEnrollment", back_populates="student")
    faculty_courses = relationship("FacultyCourseAssignment", back_populates="faculty")
    subject_expert_assignments = relationship("SubjectExpertAssignment", back_populates="faculty")
    courses = relationship("Course", back_populates="created_by_user")
    assessments = relationship("Assessment", back_populates="created_by_user")


class AdminAuditLog(Base):
    """Minimal, non-secret audit trail for administrator master-data mutations."""

    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), nullable=False, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    summary = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    actor = relationship("User")


Index(
    "uq_users_roll_number_btrim_upper",
    func.upper(func.trim(User.roll_number)),
    unique=True,
    postgresql_where=User.roll_number.is_not(None),
    sqlite_where=User.roll_number.is_not(None),
)
Index(
    "uq_users_employee_code_btrim_upper",
    func.upper(func.trim(User.employee_code)),
    unique=True,
    postgresql_where=User.employee_code.is_not(None),
    sqlite_where=User.employee_code.is_not(None),
)


class AuthChallenge(Base):
    """Hashed, short-lived OTP and restricted authorization state."""

    __tablename__ = "auth_challenges"

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    purpose = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    subject_hash = Column(String(64), nullable=False, index=True)
    contact_hash = Column(String(64), nullable=True)
    otp_hash = Column(String(64), nullable=True)
    status = Column(String(24), nullable=False, server_default="PENDING", default="PENDING")
    failed_attempts = Column(Integer, nullable=False, server_default="0", default=0)
    send_count = Column(Integer, nullable=False, server_default="1", default=1)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    resend_available_at = Column(DateTime(timezone=True), nullable=False)
    authorization_hash = Column(String(64), nullable=True)
    authorization_expires_at = Column(DateTime(timezone=True), nullable=True)
    authorization_used_at = Column(DateTime(timezone=True), nullable=True)
    request_ip_hash = Column(String(64), nullable=False, index=True)
    delivery_status = Column(String(24), nullable=False, server_default="PENDING", default="PENDING")
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =========================
# Course Model
# =========================

class Course(Base):
    """SYS Course = a goal-oriented preparation / learning programme."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    syllabus_url = Column(String(255), nullable=True)
    resources_url = Column(String(255), nullable=True)
    # P0-018 programme classification (existing rows default via migration)
    programme_category = Column(
        String(50), nullable=False, server_default="INDEPENDENT_LEARNING", default="INDEPENDENT_LEARNING"
    )
    examination_name = Column(String(200), nullable=True)
    examination_authority = Column(String(200), nullable=True)
    target_purpose = Column(String(300), nullable=True)
    programme_code = Column(String(80), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollments = relationship("StudentCourseEnrollment", back_populates="course")
    faculty_assignments = relationship("FacultyCourseAssignment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")
    resources = relationship("Resource", back_populates="course")
    subjects = relationship("Subject", back_populates="course")
    created_by_user = relationship("User", back_populates="courses")
    questions = relationship("Question", back_populates="course")


class StudentCourseEnrollment(Base):
    __tablename__ = "student_course_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class FacultyCourseAssignment(Base):
    """Course Coordinator academic responsibility (not a system role)."""
    __tablename__ = "faculty_course_assignments"
    __table_args__ = (
        UniqueConstraint("faculty_id", "course_id", name="uq_faculty_course_coordinator"),
    )

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    faculty = relationship("User", back_populates="faculty_courses")
    course = relationship("Course", back_populates="faculty_assignments")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="subjects")
    expert_assignments = relationship("SubjectExpertAssignment", back_populates="subject")
    topics = relationship("Topic", back_populates="subject")
    questions = relationship("Question", back_populates="subject")


class SubjectExpertAssignment(Base):
    __tablename__ = "subject_expert_assignments"
    __table_args__ = (
        UniqueConstraint("faculty_id", "subject_id", name="uq_faculty_subject_expert"),
    )

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    faculty = relationship("User", back_populates="subject_expert_assignments")
    subject = relationship("Subject", back_populates="expert_assignments")


# =========================
# Topic / Subtopic
# =========================

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="topics")
    subtopics = relationship("Subtopic", back_populates="topic")
    questions = relationship("Question", back_populates="topic")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topic = relationship("Topic", back_populates="subtopics")
    questions = relationship("Question", back_populates="subtopic")


# =========================
# Question Bank boundary (P0-009 / P0-010)
# =========================

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    stem = Column(Text, nullable=False)  # question_text
    question_type = Column(String(50), nullable=False, server_default="SINGLE_MCQ")
    difficulty = Column(String(20), nullable=False, server_default="MEDIUM")
    status = Column(String(20), nullable=False, server_default="DRAFT")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # P0-010 intelligence fields
    options = Column(JSON, nullable=True)
    correct_answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    marks = Column(Float, nullable=True, default=1.0)
    negative_marks = Column(Float, nullable=True, default=0.0)
    source = Column(String(100), nullable=True)
    source_year = Column(Integer, nullable=True)
    exam_name = Column(String(200), nullable=True)
    concept_tags = Column(JSON, nullable=True)
    learning_objective = Column(String(500), nullable=True)
    shortcut = Column(Text, nullable=True)
    alternative_solution = Column(Text, nullable=True)
    common_traps = Column(Text, nullable=True)
    estimated_time_seconds = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    similarity_fingerprint = Column(String(64), nullable=True, index=True)
    novelty_class = Column(String(30), nullable=True, server_default="NOVEL")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course", back_populates="questions")
    subject = relationship("Subject", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    subtopic = relationship("Subtopic", back_populates="questions")


# =========================
# Assessment Model (extended P0-009)
# =========================

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # P0-009 fields
    category = Column(String(50), nullable=True)
    assessment_type = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, server_default="DRAFT", default="DRAFT")
    duration_minutes = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    total_marks = Column(Float, nullable=True)
    marks_correct = Column(Float, nullable=True, default=1.0)
    marks_incorrect = Column(Float, nullable=True, default=0.0)
    marks_unanswered = Column(Float, nullable=True, default=0.0)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # P0-011 availability / attempt policy
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    max_attempts = Column(Integer, nullable=False, server_default="1", default=1)
    answer_key_released = Column(Boolean, nullable=False, server_default="false", default=False)

    course = relationship("Course", back_populates="assessments")
    created_by_user = relationship("User", back_populates="assessments")
    subject = relationship("Subject")
    topic = relationship("Topic")
    blueprint_items = relationship(
        "AssessmentBlueprintItem",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "AssessmentVersion",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    attempts = relationship("AssessmentAttempt", back_populates="assessment")


class AssessmentBlueprintItem(Base):
    __tablename__ = "assessment_blueprint_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    difficulty = Column(String(20), nullable=False)
    question_count = Column(Integer, nullable=False)

    assessment = relationship("Assessment", back_populates="blueprint_items")
    subject = relationship("Subject")
    topic = relationship("Topic")
    subtopic = relationship("Subtopic")


class AssessmentVersion(Base):
    """Immutable published snapshot of an assessment."""
    __tablename__ = "assessment_versions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "version_number", name="uq_assessment_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    blueprint_snapshot = Column(JSON, nullable=True)
    marking_snapshot = Column(JSON, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    total_marks = Column(Float, nullable=True)
    category = Column(String(50), nullable=True)
    assessment_type = Column(String(50), nullable=True)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    assessment = relationship("Assessment", back_populates="versions")
    questions = relationship(
        "AssessmentQuestion",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    attempts = relationship("AssessmentAttempt", back_populates="version")


class AssessmentQuestion(Base):
    """Frozen question membership + immutable content snapshot for a published version."""
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint("version_id", "question_id", name="uq_version_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("assessment_versions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    sequence = Column(Integer, nullable=False, default=1)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    difficulty = Column(String(20), nullable=True)
    marks_available = Column(Float, nullable=False, default=1.0)
    # Immutable snapshot (P0-011) — answer keys / evaluation must use these
    stem_snapshot = Column(Text, nullable=True)
    options_snapshot = Column(JSON, nullable=True)
    correct_answer_snapshot = Column(Text, nullable=True)
    explanation_snapshot = Column(Text, nullable=True)
    question_type_snapshot = Column(String(50), nullable=True)
    shortcut_snapshot = Column(Text, nullable=True)
    alternative_solution_snapshot = Column(Text, nullable=True)
    common_traps_snapshot = Column(Text, nullable=True)
    negative_marks_snapshot = Column(Float, nullable=True)
    subject_name_snapshot = Column(String(200), nullable=True)
    topic_name_snapshot = Column(String(200), nullable=True)

    version = relationship("AssessmentVersion", back_populates="questions")
    question = relationship("Question")


# =========================
# Attempts / Performance records (Analyzer contract)
# =========================

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("assessment_versions.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, server_default="IN_PROGRESS", default="IN_PROGRESS")
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    auto_submitted = Column(Boolean, nullable=False, server_default="false", default=False)
    time_spent_seconds = Column(Float, nullable=True)
    total_marks_obtained = Column(Float, nullable=True)
    total_marks_available = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    correct_count = Column(Integer, nullable=True)
    incorrect_count = Column(Integer, nullable=True)
    unanswered_count = Column(Integer, nullable=True)

    assessment = relationship("Assessment", back_populates="attempts")
    version = relationship("AssessmentVersion", back_populates="attempts")
    student = relationship("User")
    answer_responses = relationship(
        "AttemptResponse",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )
    responses = relationship(
        "PerformanceRecord",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class AttemptResponse(Base):
    """In-progress / submitted student answers (pre-evaluation)."""
    __tablename__ = "attempt_responses"
    __table_args__ = (
        UniqueConstraint("attempt_id", "assessment_question_id", name="uq_attempt_aq"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=False)
    assessment_question_id = Column(Integer, ForeignKey("assessment_questions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_sequence = Column(Integer, nullable=False, default=1)
    selected_answer = Column(Text, nullable=True)
    answered = Column(Boolean, nullable=False, server_default="false", default=False)
    marked_for_review = Column(Boolean, nullable=False, server_default="false", default=False)
    time_spent_seconds = Column(Float, nullable=True, default=0)
    submitted_answer_snapshot = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attempt = relationship("AssessmentAttempt", back_populates="answer_responses")
    assessment_question = relationship("AssessmentQuestion")


class PerformanceRecord(Base):
    """Granular per-question performance for future Performance Analyzer."""
    __tablename__ = "performance_records"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    assessment_version_id = Column(Integer, ForeignKey("assessment_versions.id"), nullable=False)
    assessment_category = Column(String(50), nullable=True)
    assessment_type = Column(String(50), nullable=True)
    assessment_date = Column(DateTime(timezone=True), nullable=True)

    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)

    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_type = Column(String(50), nullable=True)
    difficulty = Column(String(20), nullable=True)

    marks_available = Column(Float, nullable=False, default=0)
    marks_obtained = Column(Float, nullable=False, default=0)
    is_correct = Column(Boolean, nullable=False, default=False)
    is_incorrect = Column(Boolean, nullable=False, default=False)
    is_unanswered = Column(Boolean, nullable=False, default=False)
    response_time_seconds = Column(Float, nullable=True)
    negative_marks = Column(Float, nullable=True, default=0)
    attempt_number = Column(Integer, nullable=False, default=1)

    attempt = relationship("AssessmentAttempt", back_populates="responses")


# =========================
# Notifications
# =========================

class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=True)
    email = Column(String(255), nullable=False)
    recipient_type = Column(String(50), nullable=False, server_default="CUSTOM_RECIPIENT")
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    # JSON list of event codes; null/empty = all events
    event_types = Column(JSON, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    frequency = Column(String(50), nullable=False, server_default="IMMEDIATE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String(50), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipients = Column(JSON, nullable=False, default=list)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="PENDING")
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, server_default="0", default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    # P0-012 unified engine fields
    source_module = Column(String(50), nullable=True, server_default="SYSTEM")
    severity = Column(String(20), nullable=True, server_default="INFO")
    priority = Column(Integer, nullable=True, default=5)
    title = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    link_path = Column(String(500), nullable=True)
    channels = Column(JSON, nullable=True)  # ["EMAIL","IN_APP"]

    deliveries = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
    )


class NotificationDelivery(Base):
    """Per-recipient, per-channel delivery audit (P0-012)."""
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=True)
    channel = Column(String(20), nullable=False)  # EMAIL | IN_APP | SMS
    status = Column(String(20), nullable=False, server_default="PENDING")
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, server_default="0", default=0)
    is_read = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    notification = relationship("Notification", back_populates="deliveries")
    user = relationship("User")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_notif_pref_category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), nullable=False)
    email_enabled = Column(Boolean, nullable=False, server_default="true", default=True)
    in_app_enabled = Column(Boolean, nullable=False, server_default="true", default=True)
    sms_enabled = Column(Boolean, nullable=False, server_default="false", default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")


class PerformanceAnalysis(Base):
    """Cached analyzer output for a student+course (from real PerformanceRecords)."""
    __tablename__ = "performance_analyses"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_perf_analysis_student_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    analysis_json = Column(JSON, nullable=False)
    overall_percentage = Column(Float, nullable=True)
    trend = Column(String(30), nullable=True)
    readiness_estimate = Column(Float, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    trigger_attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=True)


class LearningGap(Base):
    __tablename__ = "learning_gaps"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("performance_analyses.id"), nullable=True)
    scope_type = Column(String(30), nullable=False)  # SUBJECT|TOPIC|CONCEPT|DIFFICULTY
    scope_id = Column(Integer, nullable=True)
    scope_name = Column(String(200), nullable=True)
    classification = Column(String(30), nullable=False)
    confidence = Column(Float, nullable=True)
    priority_score = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)  # observed
    inference = Column(JSON, nullable=True)  # system inference (not facts)
    is_high_priority = Column(Boolean, nullable=False, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudentLearningProfile(Base):
    """Machine-readable profile for AI Lecturer / Remedial consumers."""
    __tablename__ = "student_learning_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_learning_profile_student_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    profile_json = Column(JSON, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis_id = Column(Integer, ForeignKey("performance_analyses.id"), nullable=True)


# =========================
# Question Intelligence (P0-010)
# =========================

class HistoricalExamPaper(Base):
    __tablename__ = "historical_exam_papers"

    id = Column(Integer, primary_key=True, index=True)
    exam_name = Column(String(200), nullable=False)
    exam_year = Column(Integer, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    exam_type = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course")
    questions = relationship(
        "HistoricalExamQuestion",
        back_populates="paper",
        cascade="all, delete-orphan",
    )


class HistoricalExamQuestion(Base):
    __tablename__ = "historical_exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("historical_exam_papers.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)
    marks = Column(Float, nullable=True)
    difficulty = Column(String(20), nullable=True)
    concept_tags = Column(JSON, nullable=True)
    linked_question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    similarity_class = Column(String(30), nullable=True, server_default="CONCEPT_VARIANT")
    fingerprint = Column(String(64), nullable=True, index=True)

    paper = relationship("HistoricalExamPaper", back_populates="questions")


class SubjectWeightage(Base):
    __tablename__ = "subject_weightages"
    __table_args__ = (UniqueConstraint("course_id", "subject_id", name="uq_course_subject_weight"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    weight_percent = Column(Float, nullable=False)


class TopicWeightage(Base):
    __tablename__ = "topic_weightages"
    __table_args__ = (UniqueConstraint("subject_id", "topic_id", name="uq_subject_topic_weight"),)

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    weight_percent = Column(Float, nullable=False)
    syllabus_importance = Column(Float, nullable=True, default=0.5)


class PriorityWeightConfig(Base):
    """Configurable factor weights for topic priority (must sum ≈ 1.0)."""
    __tablename__ = "priority_weight_configs"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, unique=True)
    w_historical_weightage = Column(Float, nullable=False, default=0.25)
    w_historical_frequency = Column(Float, nullable=False, default=0.25)
    w_concept_frequency = Column(Float, nullable=False, default=0.15)
    w_recent_trend = Column(Float, nullable=False, default=0.15)
    w_syllabus_importance = Column(Float, nullable=False, default=0.10)
    w_exam_pattern = Column(Float, nullable=False, default=0.10)


class TopicIntelligenceSnapshot(Base):
    __tablename__ = "topic_intelligence_snapshots"
    __table_args__ = (UniqueConstraint("topic_id", "course_id", name="uq_topic_course_intel"),)

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    historical_frequency = Column(Float, nullable=True)
    avg_marks_weightage = Column(Float, nullable=True)
    recent_trend = Column(String(20), nullable=True)
    priority_score = Column(Float, nullable=True)
    priority_label = Column(String(20), nullable=True)
    contributing_factors = Column(JSON, nullable=True)
    question_count = Column(Integer, nullable=True, default=0)
    frequently_tested_concepts = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =========================
# Learning Sessions (P0-013)
# =========================

class LearningSession(Base):
    """Reusable multi-mode learning session (COMMON / INDIVIDUAL / HYBRID)."""
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    mode = Column(String(20), nullable=False)  # COMMON | INDIVIDUAL | HYBRID
    status = Column(String(20), nullable=False, server_default="DRAFT", default="DRAFT")

    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)

    facilitator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    outcome_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
    subtopic = relationship("Subtopic")
    facilitator = relationship("User", foreign_keys=[facilitator_id])
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship(
        "LearningSessionParticipant",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    objectives = relationship(
        "LearningSessionObjective",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    activities = relationship(
        "LearningSessionActivity",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    evidence = relationship(
        "LearningEvidence",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class LearningSessionParticipant(Base):
    __tablename__ = "learning_session_participants"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_learning_session_participant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(30), nullable=False, server_default="STUDENT", default="STUDENT")
    status = Column(String(20), nullable=False, server_default="INVITED", default="INVITED")
    joined_at = Column(DateTime(timezone=True), nullable=True)
    left_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("LearningSession", back_populates="participants")
    user = relationship("User")


class LearningSessionObjective(Base):
    __tablename__ = "learning_session_objectives"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False, index=True)
    statement = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, server_default="PENDING", default="PENDING")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    concept_tag = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("LearningSession", back_populates="objectives")


class LearningSessionActivity(Base):
    __tablename__ = "learning_session_activities"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    sequence = Column(Integer, nullable=False, default=1)
    # COMMON = all participants; PARTICIPANT_SPECIFIC = one participant (hybrid/individual)
    scope = Column(String(30), nullable=False, server_default="COMMON", default="COMMON")
    participant_id = Column(
        Integer, ForeignKey("learning_session_participants.id"), nullable=True, index=True
    )
    status = Column(String(20), nullable=False, server_default="PENDING", default="PENDING")
    payload = Column(JSON, nullable=True)
    # Optional link to existing assessment (P0-010/011) — no duplicate attempt engine
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    session = relationship("LearningSession", back_populates="activities")
    participant = relationship("LearningSessionParticipant", foreign_keys=[participant_id])
    assessment = relationship("Assessment")


class LearningEvidence(Base):
    """Session learning evidence foundation for future P0-012 consumption."""
    __tablename__ = "learning_evidence"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    participant_id = Column(Integer, ForeignKey("learning_session_participants.id"), nullable=True)
    activity_id = Column(Integer, ForeignKey("learning_session_activities.id"), nullable=True)
    objective_id = Column(Integer, ForeignKey("learning_session_objectives.id"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("LearningSession", back_populates="evidence")
    user = relationship("User")
    participant = relationship("LearningSessionParticipant", foreign_keys=[participant_id])
    activity = relationship("LearningSessionActivity", foreign_keys=[activity_id])
    objective = relationship("LearningSessionObjective", foreign_keys=[objective_id])


# =========================
# Remedial Learning (P0-014)
# =========================

class RemedialGroup(Base):
    """Explainable remedial cohort formed from similar P0-012 learning gaps."""
    __tablename__ = "remedial_groups"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    scope_type = Column(String(30), nullable=False)  # TOPIC|SUBJECT|CONCEPT|...
    scope_id = Column(Integer, nullable=True)
    scope_name = Column(String(200), nullable=False)
    severity = Column(String(20), nullable=False)  # low|moderate|high|critical
    status = Column(String(20), nullable=False, server_default="PROPOSED", default="PROPOSED")
    explanation = Column(JSON, nullable=False)  # why grouped
    similarity = Column(JSON, nullable=True)  # signals / score
    learning_session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
    learning_session = relationship("LearningSession", foreign_keys=[learning_session_id])
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship(
        "RemedialGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    interventions = relationship(
        "RemedialIntervention",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class RemedialGroupMember(Base):
    __tablename__ = "remedial_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_remedial_group_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("remedial_groups.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    learning_gap_id = Column(Integer, ForeignKey("learning_gaps.id", ondelete="SET NULL"), nullable=True)
    gap_snapshot = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, server_default="INVITED", default="INVITED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("RemedialGroup", back_populates="members")
    student = relationship("User", foreign_keys=[student_id])
    learning_gap = relationship("LearningGap", foreign_keys=[learning_gap_id])


class RemedialIntervention(Base):
    """Intervention plan linked to P0-013 learning session (group or individual)."""
    __tablename__ = "remedial_interventions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null for group-shared
    group_id = Column(Integer, ForeignKey("remedial_groups.id"), nullable=True, index=True)
    learning_gap_id = Column(Integer, ForeignKey("learning_gaps.id", ondelete="SET NULL"), nullable=True)
    gap_snapshot = Column(JSON, nullable=False)
    intervention_type = Column(String(50), nullable=False)
    mode = Column(String(20), nullable=False)  # COMMON|INDIVIDUAL|HYBRID
    priority_rank = Column(Integer, nullable=False, default=1)
    priority_explanation = Column(Text, nullable=True)
    plan = Column(JSON, nullable=False)
    explanation = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, server_default="DRAFT", default="DRAFT")
    outcome = Column(String(20), nullable=False, server_default="PENDING", default="PENDING")
    reassessment_required = Column(Boolean, nullable=False, server_default="false", default=False)
    reassessment_completed = Column(Boolean, nullable=False, server_default="false", default=False)
    learning_session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    course = relationship("Course")
    student = relationship("User", foreign_keys=[student_id])
    group = relationship("RemedialGroup", back_populates="interventions")
    learning_gap = relationship("LearningGap", foreign_keys=[learning_gap_id])
    learning_session = relationship("LearningSession", foreign_keys=[learning_session_id])
    creator = relationship("User", foreign_keys=[created_by])


# =========================
# Adaptive Practice & Mastery (P0-015)
# =========================

class MasteryPolicy(Base):
    """Configurable mastery thresholds (course override or global when course_id is null)."""
    __tablename__ = "mastery_policies"
    __table_args__ = (
        UniqueConstraint("course_id", name="uq_mastery_policy_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    mastery_threshold = Column(Float, nullable=False, server_default="80", default=80.0)
    practice_threshold = Column(Float, nullable=False, server_default="70", default=70.0)
    reassessment_threshold = Column(Float, nullable=False, server_default="80", default=80.0)
    min_reassessment_questions = Column(Integer, nullable=False, server_default="5", default=5)
    regression_drop_points = Column(Float, nullable=False, server_default="25", default=25.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    course = relationship("Course")


class TopicMasteryState(Base):
    """Authoritative current mastery interpretation for a student+topic (not duplicated scores)."""
    __tablename__ = "topic_mastery_states"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "topic_id", name="uq_topic_mastery_student_course_topic"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    status = Column(String(40), nullable=False, server_default="NOT_ASSESSED", default="NOT_ASSESSED")
    indicator = Column(String(20), nullable=False, server_default="GRAY", default="GRAY")
    mastery_percent = Column(Float, nullable=True)
    practice_accuracy = Column(Float, nullable=True)
    target_difficulty = Column(String(20), nullable=False, server_default="EASY", default="EASY")
    remediation_source = Column(String(40), nullable=True)
    eligibility_flags = Column(JSON, nullable=True)
    explanation = Column(JSON, nullable=True)
    last_practice_attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=True)
    last_reassessment_attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=True)
    last_decision_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", foreign_keys=[student_id])
    course = relationship("Course")
    topic = relationship("Topic")
    subject = relationship("Subject")


class MasteryEvent(Base):
    """Append-only mastery decision / practice history (preserves evidence trail)."""
    __tablename__ = "mastery_events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True)
    evidence = Column(JSON, nullable=True)
    explanation = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", foreign_keys=[student_id])


class AdaptivePracticeAssignment(Base):
    """Links adaptive practice / reassessment intents to published P0-011 assessments."""
    __tablename__ = "adaptive_practice_assignments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    purpose = Column(String(30), nullable=False)  # PRACTICE | REASSESSMENT
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    difficulty = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default="READY", default="READY")
    recommendation = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=True)

    student = relationship("User", foreign_keys=[student_id])
    assessment = relationship("Assessment")
    topic = relationship("Topic")


# =========================
# Learning Orchestration (P0-017) — coordination state only
# =========================

class LearningJourneyAction(Base):
    """Orchestration recommendation / lifecycle. Does not store mastery, gaps, or scores."""
    __tablename__ = "learning_journey_actions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    stable_key = Column(String(200), nullable=False, index=True)
    action_type = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, server_default="MEDIUM", default="MEDIUM")
    status = Column(String(20), nullable=False, server_default="RECOMMENDED", default="RECOMMENDED")
    source = Column(String(40), nullable=False)
    hierarchy_group = Column(String(40), nullable=True)
    target_subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    target_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    resource_reference = Column(JSON, nullable=True)
    prerequisites = Column(JSON, nullable=True)
    explanation = Column(JSON, nullable=True)
    mandatory = Column(Boolean, nullable=False, server_default="false", default=False)
    chosen_alternative = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    student = relationship("User", foreign_keys=[student_id])
    course = relationship("Course")
    topic = relationship("Topic", foreign_keys=[target_topic_id])
    subject = relationship("Subject", foreign_keys=[target_subject_id])


# =========================
# P0-019 Subject progression metadata (not academic facts)
# =========================

class TopicPrerequisite(Base):
    """Authoritative same-subject prerequisite edge. Empty table = no invented graph."""
    __tablename__ = "topic_prerequisites"
    __table_args__ = (
        UniqueConstraint("topic_id", "prerequisite_topic_id", name="uq_topic_prerequisite"),
    )

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    prerequisite_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topic = relationship("Topic", foreign_keys=[topic_id])
    prerequisite = relationship("Topic", foreign_keys=[prerequisite_topic_id])


class StudentSubjectFocus(Base):
    """Remembers last selected subject/topic override. Does not store mastery or scores."""
    __tablename__ = "student_subject_focus"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "subject_id", name="uq_student_course_subject_focus"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    selected_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    last_focused_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", foreign_keys=[student_id])
    course = relationship("Course")
    subject = relationship("Subject")
    selected_topic = relationship("Topic", foreign_keys=[selected_topic_id])


# =========================
# Resource Model
# =========================

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    file_url = Column(String(500), nullable=False)
    status = Column(String(50), default="Available")
    upload_date = Column(DateTime, default=datetime.utcnow)

    course_id = Column(Integer, ForeignKey("courses.id"))
    course = relationship("Course", back_populates="resources")
