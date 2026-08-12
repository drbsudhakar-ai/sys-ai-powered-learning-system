"""Add admin academic management structures (P0-008)

Revision ID: 20260812_p008_admin_academic
Revises: 20260811_assess_created_at
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p008_admin_academic"
down_revision = "20260811_assess_created_at"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL UNIQUE,
            description VARCHAR(500),
            course_id INTEGER REFERENCES courses(id),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_expert_assignments (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER NOT NULL REFERENCES users(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            assigned_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_faculty_subject_expert UNIQUE (faculty_id, subject_id)
        )
        """
    )
    # Best-effort unique coordinator pair (ignore if duplicates already exist)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_faculty_course_coordinator'
            ) THEN
                ALTER TABLE faculty_course_assignments
                ADD CONSTRAINT uq_faculty_course_coordinator UNIQUE (faculty_id, course_id);
            END IF;
        EXCEPTION WHEN unique_violation THEN
            NULL;
        END $$;
        """
    )


def downgrade():
    op.execute("ALTER TABLE faculty_course_assignments DROP CONSTRAINT IF EXISTS uq_faculty_course_coordinator")
    op.execute("DROP TABLE IF EXISTS subject_expert_assignments")
    op.execute("DROP TABLE IF EXISTS subjects")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_active")
