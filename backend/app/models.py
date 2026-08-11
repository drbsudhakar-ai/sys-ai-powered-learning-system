"""
SQLAlchemy Models
-----------------
SYS AI Lecturer System
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    enrollments = relationship("StudentCourseEnrollment", back_populates="student")
    faculty_courses = relationship("FacultyCourseAssignment", back_populates="faculty")
    courses = relationship("Course", back_populates="created_by_user")   # audit trail
    assessments = relationship("Assessment", back_populates="created_by_user")  # audit trail


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

    created_by = Column(Integer, ForeignKey("users.id"))  # faculty/admin who created
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    enrollments = relationship("StudentCourseEnrollment", back_populates="course")
    faculty_assignments = relationship("FacultyCourseAssignment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")
    resources = relationship("Resource", back_populates="course")
    created_by_user = relationship("User", back_populates="courses")  # audit trail


# =========================
# Student Course Enrollment Model
# =========================

class StudentCourseEnrollment(Base):
    __tablename__ = "student_course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


# =========================
# Faculty Course Assignment Model
# =========================

class FacultyCourseAssignment(Base):
    __tablename__ = "faculty_course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    faculty = relationship("User", back_populates="faculty_courses")
    course = relationship("Course", back_populates="faculty_assignments")


# =========================
# Assessment Model
# =========================

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))  # faculty/admin
    due_date = Column(DateTime(timezone=True), nullable=True)

    course = relationship("Course", back_populates="assessments")
    created_by_user = relationship("User", back_populates="assessments")  # audit trail


# =========================
# Resource Model
# =========================

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # PDF, Word, Image, Video
    file_url = Column(String(500), nullable=False)
    status = Column(String(50), default="Available")
    upload_date = Column(DateTime, default=datetime.utcnow)

    course_id = Column(Integer, ForeignKey("courses.id"))
    course = relationship("Course", back_populates="resources")
