"""P0-019 Subject progression, optional prerequisites, and course balance.

Revision ID: 20260815_p019_subject
Revises: 20260815_p018_programme
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_p019_subject"
down_revision = "20260815_p018_programme"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_prerequisites (
            id SERIAL PRIMARY KEY,
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            prerequisite_topic_id INTEGER NOT NULL REFERENCES topics(id),
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_topic_prerequisite UNIQUE (topic_id, prerequisite_topic_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_topic_prerequisites_topic_id ON topic_prerequisites(topic_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_topic_prerequisites_prereq_id ON topic_prerequisites(prerequisite_topic_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS student_subject_focus (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            selected_topic_id INTEGER REFERENCES topics(id),
            last_focused_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_student_course_subject_focus UNIQUE (student_id, course_id, subject_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ssf_student_id ON student_subject_focus(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ssf_course_id ON student_subject_focus(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ssf_subject_id ON student_subject_focus(subject_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS student_subject_focus")
    op.execute("DROP TABLE IF EXISTS topic_prerequisites")
