"""Add created_at to assessments

Revision ID: 20260811_assess_created_at
Revises: 20260808_sys_ai_models
Create Date: 2026-08-11
"""

from alembic import op

revision = "20260811_assess_created_at"
down_revision = "20260808_sys_ai_models"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE assessments "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()"
    )


def downgrade():
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS created_at")
