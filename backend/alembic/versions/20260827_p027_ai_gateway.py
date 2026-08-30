"""Encrypted AI configuration and durable organization-wide usage reservations."""
from alembic import op
import sqlalchemy as sa

revision = "20260827_p027_ai_gateway"
down_revision = "20260826_p026_enrollment"
branch_labels = None
depends_on = None


def upgrade():
    # Older installations run metadata.create_all at startup before Alembic.
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "ai_provider_settings" not in tables:
        op.create_table("ai_provider_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("label", sa.String(100), nullable=False),
            sa.Column("protocol", sa.String(32), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=False),
            sa.Column("model", sa.String(160), nullable=False),
            sa.Column("encrypted_key", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            *[sa.Column(name, sa.Integer(), nullable=False) for name in
              ("daily_requests", "daily_tokens", "minute_requests", "minute_tokens", "student_daily_requests", "max_output_tokens", "revision")],
            sa.CheckConstraint("id = 1", name="ck_ai_settings_singleton"))
    if "ai_usage_events" not in tables:
        op.create_table("ai_usage_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("provider_label", sa.String(100), nullable=False),
            sa.Column("model", sa.String(160), nullable=False),
            sa.Column("purpose", sa.String(64), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("budget_tokens", sa.Integer(), nullable=False),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("error_code", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("ix_ai_usage_events_created_at", "ai_usage_events", ["created_at"])


def downgrade():
    op.drop_table("ai_usage_events")
    op.drop_table("ai_provider_settings")
