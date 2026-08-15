"""P0-017 Personalized Learning Journey orchestration state

Revision ID: 20260815_p017_journey
Revises: 20260815_p015_mastery
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_p017_journey"
down_revision = "20260815_p015_mastery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_journey_actions (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            stable_key VARCHAR(200) NOT NULL,
            action_type VARCHAR(40) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            reason TEXT NOT NULL,
            priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            status VARCHAR(20) NOT NULL DEFAULT 'RECOMMENDED',
            source VARCHAR(40) NOT NULL,
            hierarchy_group VARCHAR(40),
            target_subject_id INTEGER REFERENCES subjects(id),
            target_topic_id INTEGER REFERENCES topics(id),
            resource_reference JSONB,
            prerequisites JSONB,
            explanation JSONB,
            mandatory BOOLEAN NOT NULL DEFAULT false,
            chosen_alternative VARCHAR(40),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            last_notified_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_lja_student_id ON learning_journey_actions(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lja_course_id ON learning_journey_actions(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lja_stable_key ON learning_journey_actions(stable_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lja_status ON learning_journey_actions(status)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS learning_journey_actions")
