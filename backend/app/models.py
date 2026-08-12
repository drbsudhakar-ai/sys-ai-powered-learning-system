"""
SQLAlchemy Models
-----------------
SYS AI Lecturer System
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
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

    # Relationships
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


# =========================
# Student Course Enrollment
# =========================

class StudentCourseEnrollment(Base):
    __tablename__ = "student_course_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


# =========================
# Faculty Course Assignment = Course Coordinator responsibility
# =========================

class FacultyCourseAssignment(Base):
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


# =========================
# Subject (minimal academic entity)
# =========================

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="subjects")
    expert_assignments = relationship("SubjectExpertAssignment", back_populates="subject")


# =========================
# Subject Expert Assignment (academic responsibility)
# =========================

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
# Assessment Model
# =========================

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="assessments")
    created_by_user = relationship("User", back_populates="assessments")


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
