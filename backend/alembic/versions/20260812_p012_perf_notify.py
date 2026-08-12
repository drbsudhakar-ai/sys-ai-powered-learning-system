"""P0-012 Performance Analyzer + Unified Notification Engine

Revision ID: 20260812_p012_perf_notify
Revises: 20260812_p011_attempts
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p012_perf_notify"
down_revision = "20260812_p011_attempts"
branch_labels = None
depends_on = None


def upgrade():
    for stmt in [
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS source_module VARCHAR(50) DEFAULT 'SYSTEM'",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'INFO'",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS title VARCHAR(255)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS payload JSONB",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link_path VARCHAR(500)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channels JSONB",
    ]:
        op.execute(stmt)

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_deliveries (
            id SERIAL PRIMARY KEY,
            notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            email VARCHAR(255),
            channel VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            failure_reason TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            sent_at TIMESTAMPTZ,
            read_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            category VARCHAR(50) NOT NULL,
            email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            sms_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_user_notif_pref_category UNIQUE (user_id, category)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS performance_analyses (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            analysis_json JSONB NOT NULL,
            overall_percentage DOUBLE PRECISION,
            trend VARCHAR(30),
            readiness_estimate DOUBLE PRECISION,
            generated_at TIMESTAMPTZ DEFAULT now(),
            trigger_attempt_id INTEGER REFERENCES assessment_attempts(id),
            CONSTRAINT uq_perf_analysis_student_course UNIQUE (student_id, course_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_gaps (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            analysis_id INTEGER REFERENCES performance_analyses(id),
            scope_type VARCHAR(30) NOT NULL,
            scope_id INTEGER,
            scope_name VARCHAR(200),
            classification VARCHAR(30) NOT NULL,
            confidence DOUBLE PRECISION,
            priority_score DOUBLE PRECISION,
            evidence JSONB,
            inference JSONB,
            is_high_priority BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS student_learning_profiles (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            profile_json JSONB NOT NULL,
            generated_at TIMESTAMPTZ DEFAULT now(),
            analysis_id INTEGER REFERENCES performance_analyses(id),
            CONSTRAINT uq_learning_profile_student_course UNIQUE (student_id, course_id)
        )
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS student_learning_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS learning_gaps CASCADE")
    op.execute("DROP TABLE IF EXISTS performance_analyses CASCADE")
    op.execute("DROP TABLE IF EXISTS notification_preferences CASCADE")
    op.execute("DROP TABLE IF EXISTS notification_deliveries CASCADE")
    for col in ["source_module", "severity", "priority", "title", "payload", "link_path", "channels"]:
        op.execute(f"ALTER TABLE notifications DROP COLUMN IF EXISTS {col}")
