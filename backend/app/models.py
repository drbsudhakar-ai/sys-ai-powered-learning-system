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
    DateTime,
    ForeignKey,
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

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # "student", "faculty", "admin"
    roll_number = Column(String(50), nullable=True)
    employee_code = Column(String(50), nullable=True)
    photo_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    enrollments = relationship("StudentCourseEnrollment", back_populates="student")
    faculty_courses = relationship("FacultyCourseAssignment", back_populates="faculty")
    subject_expert_assignments = relationship("SubjectExpertAssignment", back_populates="faculty")
    courses = relationship("Course", back_populates="created_by_user")
    assessments = relationship("Assessment", back_populates="created_by_user")


# =========================
# Course Model
# =========================

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    syllabus_url = Column(String(255), nullable=True)
    resources_url = Column(String(255), nullable=True)

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
    stem = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, server_default="MCQ")
    difficulty = Column(String(20), nullable=False, server_default="MEDIUM")
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
    """Frozen question membership for a published assessment version."""
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
    status = Column(String(20), nullable=False, server_default="SUBMITTED")
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    total_marks_obtained = Column(Float, nullable=True)
    total_marks_available = Column(Float, nullable=True)

    assessment = relationship("Assessment", back_populates="attempts")
    version = relationship("AssessmentVersion", back_populates="attempts")
    student = relationship("User")
    responses = relationship(
        "PerformanceRecord",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


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
