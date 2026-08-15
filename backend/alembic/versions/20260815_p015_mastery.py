"""P0-015 Adaptive Practice & Mastery Engine

Revision ID: 20260815_p015_mastery
Revises: 20260815_p014_remedial
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_p015_mastery"
down_revision = "20260815_p014_remedial"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mastery_policies (
            id SERIAL PRIMARY KEY,
            course_id INTEGER REFERENCES courses(id),
            mastery_threshold DOUBLE PRECISION NOT NULL DEFAULT 80,
            practice_threshold DOUBLE PRECISION NOT NULL DEFAULT 70,
            reassessment_threshold DOUBLE PRECISION NOT NULL DEFAULT 80,
            min_reassessment_questions INTEGER NOT NULL DEFAULT 5,
            regression_drop_points DOUBLE PRECISION NOT NULL DEFAULT 25,
            updated_at TIMESTAMPTZ DEFAULT now(),
            updated_by INTEGER REFERENCES users(id),
            CONSTRAINT uq_mastery_policy_course UNIQUE (course_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mastery_policies_course_id ON mastery_policies(course_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_mastery_states (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            subject_id INTEGER REFERENCES subjects(id),
            status VARCHAR(40) NOT NULL DEFAULT 'NOT_ASSESSED',
            indicator VARCHAR(20) NOT NULL DEFAULT 'GRAY',
            mastery_percent DOUBLE PRECISION,
            practice_accuracy DOUBLE PRECISION,
            target_difficulty VARCHAR(20) NOT NULL DEFAULT 'EASY',
            remediation_source VARCHAR(40),
            eligibility_flags JSONB,
            explanation JSONB,
            last_practice_attempt_id INTEGER REFERENCES assessment_attempts(id),
            last_reassessment_attempt_id INTEGER REFERENCES assessment_attempts(id),
            last_decision_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ DEFAULT now(),
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_topic_mastery_student_course_topic UNIQUE (student_id, course_id, topic_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_topic_mastery_states_student_id ON topic_mastery_states(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_topic_mastery_states_course_id ON topic_mastery_states(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_topic_mastery_states_topic_id ON topic_mastery_states(topic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_topic_mastery_states_status ON topic_mastery_states(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mastery_events (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            event_type VARCHAR(50) NOT NULL,
            from_status VARCHAR(40),
            to_status VARCHAR(40),
            attempt_id INTEGER REFERENCES assessment_attempts(id),
            assessment_id INTEGER REFERENCES assessments(id),
            evidence JSONB,
            explanation JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mastery_events_student_id ON mastery_events(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mastery_events_course_id ON mastery_events(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mastery_events_topic_id ON mastery_events(topic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mastery_events_event_type ON mastery_events(event_type)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS adaptive_practice_assignments (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            purpose VARCHAR(30) NOT NULL,
            assessment_id INTEGER NOT NULL REFERENCES assessments(id),
            difficulty VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'READY',
            recommendation JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            completed_attempt_id INTEGER REFERENCES assessment_attempts(id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptive_practice_assignments_student_id "
        "ON adaptive_practice_assignments(student_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptive_practice_assignments_course_id "
        "ON adaptive_practice_assignments(course_id)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS adaptive_practice_assignments")
    op.execute("DROP TABLE IF EXISTS mastery_events")
    op.execute("DROP TABLE IF EXISTS topic_mastery_states")
    op.execute("DROP TABLE IF EXISTS mastery_policies")
