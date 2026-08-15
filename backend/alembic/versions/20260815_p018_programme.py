"""P0-018 Course / programme foundation alignment

Adds programme classification and exam metadata to existing courses.
Existing rows remain valid with INDEPENDENT_LEARNING + is_active=true.

Revision ID: 20260815_p018_programme
Revises: 20260815_p017_journey
Create Date: 2026-08-15
"""

from alembic import op

revision = "20260815_p018_programme"
down_revision = "20260815_p017_journey"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS programme_category VARCHAR(50) NOT NULL DEFAULT 'INDEPENDENT_LEARNING'
        """
    )
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS examination_name VARCHAR(200)")
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS examination_authority VARCHAR(200)")
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS target_purpose VARCHAR(300)")
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS programme_code VARCHAR(80)")
    op.execute(
        """
        ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_courses_programme_code ON courses(programme_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_courses_programme_category ON courses(programme_category)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_courses_programme_code")
    op.execute("DROP INDEX IF EXISTS ix_courses_programme_category")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS programme_code")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS target_purpose")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS examination_authority")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS examination_name")
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS programme_category")
