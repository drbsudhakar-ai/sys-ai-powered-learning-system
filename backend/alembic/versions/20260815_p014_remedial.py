"""P0-014 Intelligent Remedial Learning & Student Group Formation

Revision ID: 20260815_p014_remedial
Revises: 20260812_p013_learning_sessions
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_p014_remedial"
down_revision = "20260812_p013_learning_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS remedial_groups (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            scope_type VARCHAR(30) NOT NULL,
            scope_id INTEGER,
            scope_name VARCHAR(200) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PROPOSED',
            explanation JSONB NOT NULL,
            similarity JSONB,
            learning_session_id INTEGER REFERENCES learning_sessions(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            activated_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_remedial_groups_course_id ON remedial_groups(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_remedial_groups_subject_id ON remedial_groups(subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_remedial_groups_topic_id ON remedial_groups(topic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_remedial_groups_status ON remedial_groups(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS remedial_group_members (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES remedial_groups(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id),
            learning_gap_id INTEGER REFERENCES learning_gaps(id) ON DELETE SET NULL,
            gap_snapshot JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'INVITED',
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_remedial_group_member UNIQUE (group_id, student_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_group_members_group_id ON remedial_group_members(group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_group_members_student_id ON remedial_group_members(student_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS remedial_interventions (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            student_id INTEGER REFERENCES users(id),
            group_id INTEGER REFERENCES remedial_groups(id) ON DELETE CASCADE,
            learning_gap_id INTEGER REFERENCES learning_gaps(id) ON DELETE SET NULL,
            gap_snapshot JSONB NOT NULL,
            intervention_type VARCHAR(50) NOT NULL,
            mode VARCHAR(20) NOT NULL,
            priority_rank INTEGER NOT NULL DEFAULT 1,
            priority_explanation TEXT,
            plan JSONB NOT NULL,
            explanation JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            outcome VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            reassessment_required BOOLEAN NOT NULL DEFAULT false,
            reassessment_completed BOOLEAN NOT NULL DEFAULT false,
            learning_session_id INTEGER REFERENCES learning_sessions(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_interventions_course_id ON remedial_interventions(course_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_interventions_student_id ON remedial_interventions(student_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_interventions_group_id ON remedial_interventions(group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_remedial_interventions_status ON remedial_interventions(status)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS remedial_interventions")
    op.execute("DROP TABLE IF EXISTS remedial_group_members")
    op.execute("DROP TABLE IF EXISTS remedial_groups")
