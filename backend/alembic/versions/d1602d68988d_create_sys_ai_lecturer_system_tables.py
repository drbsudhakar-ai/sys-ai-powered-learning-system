"""Create SYS AI Lecturer System tables

Revision ID: 20260808_sys_ai_models
Revises: None
Create Date: 2026-08-08 22:30:00
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "20260808_sys_ai_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # =========================
    # Users Table
    # =========================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),  # student/faculty/admin
        sa.Column("roll_number", sa.String(50), nullable=True),
        sa.Column("employee_code", sa.String(50), nullable=True),
        sa.Column("photo_url", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # =========================
    # Courses Table
    # =========================
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("syllabus_url", sa.String(255), nullable=True),
        sa.Column("resources_url", sa.String(255), nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================
    # Student Course Enrollments
    # =========================
    op.create_table(
        "student_course_enrollments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================
    # Faculty Course Assignments
    # =========================
    op.create_table(
        "faculty_course_assignments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("faculty_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # =========================
    # Assessments Table
    # =========================
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )

    # =========================
    # Resources Table
    # =========================
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),  # PDF, Word, Image, Video
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), default="Available"),
        sa.Column("upload_date", sa.DateTime, default=sa.func.now()),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id")),
    )


def downgrade():
    op.drop_table("resources")
    op.drop_table("assessments")
    op.drop_table("faculty_course_assignments")
    op.drop_table("student_course_enrollments")
    op.drop_table("courses")
    op.drop_table("users")
