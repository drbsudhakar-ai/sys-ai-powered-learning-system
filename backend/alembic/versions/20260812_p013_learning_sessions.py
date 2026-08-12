"""P0-013.1 Learning Session domain & persistence foundation

Revision ID: 20260812_p013_learning_sessions
Revises: 20260812_p012_perf_notify
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p013_learning_sessions"
down_revision = "20260812_p012_perf_notify"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_sessions (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            mode VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            course_id INTEGER NOT NULL REFERENCES courses(id),
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            facilitator_id INTEGER REFERENCES users(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            scheduled_start TIMESTAMPTZ,
            scheduled_end TIMESTAMPTZ,
            actual_start TIMESTAMPTZ,
            actual_end TIMESTAMPTZ,
            outcome_summary JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_sessions_course_id ON learning_sessions(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_sessions_subject_id ON learning_sessions(subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_sessions_topic_id ON learning_sessions(topic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_sessions_status ON learning_sessions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_sessions_mode ON learning_sessions(mode)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_session_participants (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            role VARCHAR(30) NOT NULL DEFAULT 'STUDENT',
            status VARCHAR(20) NOT NULL DEFAULT 'INVITED',
            joined_at TIMESTAMPTZ,
            left_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_learning_session_participant UNIQUE (session_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_learning_session_participants_session_id "
        "ON learning_session_participants(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_learning_session_participants_user_id "
        "ON learning_session_participants(user_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_session_objectives (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
            statement TEXT NOT NULL,
            sequence INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            concept_tag VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_learning_session_objectives_session_id "
        "ON learning_session_objectives(session_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_session_activities (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
            activity_type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            sequence INTEGER NOT NULL DEFAULT 1,
            scope VARCHAR(30) NOT NULL DEFAULT 'COMMON',
            participant_id INTEGER REFERENCES learning_session_participants(id),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            payload JSONB,
            assessment_id INTEGER REFERENCES assessments(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_learning_session_activities_session_id "
        "ON learning_session_activities(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_learning_session_activities_participant_id "
        "ON learning_session_activities(participant_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_evidence (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            participant_id INTEGER REFERENCES learning_session_participants(id),
            activity_id INTEGER REFERENCES learning_session_activities(id),
            objective_id INTEGER REFERENCES learning_session_objectives(id),
            event_type VARCHAR(50) NOT NULL,
            payload JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_evidence_session_id ON learning_evidence(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_evidence_user_id ON learning_evidence(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_learning_evidence_event_type ON learning_evidence(event_type)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS learning_evidence CASCADE")
    op.execute("DROP TABLE IF EXISTS learning_session_activities CASCADE")
    op.execute("DROP TABLE IF EXISTS learning_session_objectives CASCADE")
    op.execute("DROP TABLE IF EXISTS learning_session_participants CASCADE")
    op.execute("DROP TABLE IF EXISTS learning_sessions CASCADE")
