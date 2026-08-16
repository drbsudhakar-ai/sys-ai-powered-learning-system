"""Add administrator master metadata and an operations audit trail.

Revision ID: 20260816_p021_admin
Revises: 20260816_p0201_ids
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260816_p021_admin"
down_revision = "20260816_p0201_ids"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("college", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("designation", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("admission_year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("present_year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("academic_status", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("employment_status", sa.String(length=32), nullable=True))

    for column in (
        "college",
        "department",
        "designation",
        "admission_year",
        "present_year",
        "academic_status",
        "employment_status",
    ):
        op.create_index(f"ix_users_{column}", "users", [column], unique=False)

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "actor_user_id", "action", "target_type", "target_id", "created_at"):
        op.create_index(f"ix_admin_audit_logs_{column}", "admin_audit_logs", [column], unique=False)


def downgrade():
    op.drop_table("admin_audit_logs")
    for column in (
        "employment_status",
        "academic_status",
        "present_year",
        "admission_year",
        "designation",
        "department",
        "college",
    ):
        op.drop_index(f"ix_users_{column}", table_name="users")
        op.drop_column("users", column)
