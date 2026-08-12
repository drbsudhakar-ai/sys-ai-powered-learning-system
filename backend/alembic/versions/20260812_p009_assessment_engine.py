"""P0-009 Assessment Engine schema structures

Revision ID: 20260812_p009_assessment_engine
Revises: 20260812_p008_admin_academic
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p009_assessment_engine"
down_revision = "20260812_p008_admin_academic"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS topics (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description VARCHAR(500),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subtopics (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description VARCHAR(500),
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            stem TEXT NOT NULL,
            question_type VARCHAR(50) NOT NULL DEFAULT 'MCQ',
            difficulty VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            course_id INTEGER NOT NULL REFERENCES courses(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    # Extend assessments
    for stmt in [
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS assessment_type VARCHAR(50)",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS duration_minutes INTEGER",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS total_questions INTEGER",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS total_marks DOUBLE PRECISION",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS marks_correct DOUBLE PRECISION DEFAULT 1",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS marks_incorrect DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS marks_unanswered DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS subject_id INTEGER REFERENCES subjects(id)",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS topic_id INTEGER REFERENCES topics(id)",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    ]:
        op.execute(stmt)

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_blueprint_items (
            id SERIAL PRIMARY KEY,
            assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            difficulty VARCHAR(20) NOT NULL,
            question_count INTEGER NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_versions (
            id SERIAL PRIMARY KEY,
            assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            blueprint_snapshot JSONB,
            marking_snapshot JSONB,
            duration_minutes INTEGER,
            total_questions INTEGER,
            total_marks DOUBLE PRECISION,
            category VARCHAR(50),
            assessment_type VARCHAR(50),
            published_at TIMESTAMPTZ DEFAULT now(),
            published_by INTEGER REFERENCES users(id),
            CONSTRAINT uq_assessment_version UNIQUE (assessment_id, version_number)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_questions (
            id SERIAL PRIMARY KEY,
            version_id INTEGER NOT NULL REFERENCES assessment_versions(id) ON DELETE CASCADE,
            question_id INTEGER NOT NULL REFERENCES questions(id),
            sequence INTEGER NOT NULL DEFAULT 1,
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            difficulty VARCHAR(20),
            marks_available DOUBLE PRECISION NOT NULL DEFAULT 1,
            CONSTRAINT uq_version_question UNIQUE (version_id, question_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_attempts (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            assessment_id INTEGER NOT NULL REFERENCES assessments(id),
            version_id INTEGER NOT NULL REFERENCES assessment_versions(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            attempt_number INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
            started_at TIMESTAMPTZ,
            submitted_at TIMESTAMPTZ DEFAULT now(),
            total_marks_obtained DOUBLE PRECISION,
            total_marks_available DOUBLE PRECISION
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS performance_records (
            id SERIAL PRIMARY KEY,
            attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            assessment_id INTEGER NOT NULL REFERENCES assessments(id),
            assessment_version_id INTEGER NOT NULL REFERENCES assessment_versions(id),
            assessment_category VARCHAR(50),
            assessment_type VARCHAR(50),
            assessment_date TIMESTAMPTZ,
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            question_id INTEGER NOT NULL REFERENCES questions(id),
            question_type VARCHAR(50),
            difficulty VARCHAR(20),
            marks_available DOUBLE PRECISION NOT NULL DEFAULT 0,
            marks_obtained DOUBLE PRECISION NOT NULL DEFAULT 0,
            is_correct BOOLEAN NOT NULL DEFAULT FALSE,
            is_incorrect BOOLEAN NOT NULL DEFAULT FALSE,
            is_unanswered BOOLEAN NOT NULL DEFAULT FALSE,
            response_time_seconds DOUBLE PRECISION,
            negative_marks DOUBLE PRECISION DEFAULT 0,
            attempt_number INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_recipients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            designation VARCHAR(100),
            email VARCHAR(255) NOT NULL,
            recipient_type VARCHAR(50) NOT NULL DEFAULT 'CUSTOM_RECIPIENT',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            event_types JSONB,
            course_id INTEGER REFERENCES courses(id),
            frequency VARCHAR(50) NOT NULL DEFAULT 'IMMEDIATE',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            event VARCHAR(50) NOT NULL,
            assessment_id INTEGER REFERENCES assessments(id),
            course_id INTEGER REFERENCES courses(id),
            student_id INTEGER REFERENCES users(id),
            recipients JSONB NOT NULL DEFAULT '[]',
            subject VARCHAR(255),
            body TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            failure_reason TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            sent_at TIMESTAMPTZ
        )
        """
    )


def downgrade():
    for table in [
        "notifications",
        "notification_recipients",
        "performance_records",
        "assessment_attempts",
        "assessment_questions",
        "assessment_versions",
        "assessment_blueprint_items",
        "questions",
        "subtopics",
        "topics",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for col in [
        "category",
        "assessment_type",
        "status",
        "duration_minutes",
        "total_questions",
        "total_marks",
        "marks_correct",
        "marks_incorrect",
        "marks_unanswered",
        "subject_id",
        "topic_id",
        "updated_at",
    ]:
        op.execute(f"ALTER TABLE assessments DROP COLUMN IF EXISTS {col}")
