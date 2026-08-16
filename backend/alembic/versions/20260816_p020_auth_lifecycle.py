"""Controlled registration, unified login, and OTP recovery.

Revision ID: 20260816_p020_auth
Revises: 20260815_p019_subject
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260816_p020_auth"
down_revision = "20260815_p019_subject"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("institutional_email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("institutional_mobile", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("mobile_number", sa.String(20), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("mobile_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("mobile_is_personal", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column(
            "account_status",
            sa.String(32),
            nullable=False,
            server_default="PENDING_ACTIVATION",
        ),
    )
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)

    op.execute(
        """
        UPDATE users
        SET email = lower(email),
            institutional_email = lower(email),
            email_verified = TRUE,
            account_status = 'ACTIVE',
            session_version = 1
        WHERE hashed_password IS NOT NULL AND length(trim(hashed_password)) > 0
        """
    )
    op.create_check_constraint(
        "ck_users_account_status",
        "users",
        "account_status IN ('PENDING_ACTIVATION', 'ACTIVE', 'DISABLED')",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_email_normalized ON users (lower(email)) WHERE email IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_mobile_number ON users (mobile_number) WHERE mobile_number IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_roll_number_normalized ON users (upper(roll_number)) WHERE roll_number IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_employee_code_normalized ON users (upper(employee_code)) WHERE employee_code IS NOT NULL"
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("auth_challenges"):
        # Older application startup code called metadata.create_all(), which
        # could create this application-owned table ahead of its Alembic
        # revision. Adopt it only when its security-relevant shape matches.
        expected_columns = {
            "id",
            "user_id",
            "purpose",
            "channel",
            "subject_hash",
            "contact_hash",
            "otp_hash",
            "status",
            "failed_attempts",
            "send_count",
            "expires_at",
            "resend_available_at",
            "authorization_hash",
            "authorization_expires_at",
            "authorization_used_at",
            "request_ip_hash",
            "delivery_status",
            "failure_reason",
            "created_at",
            "updated_at",
        }
        columns = {column["name"]: column for column in inspector.get_columns("auth_challenges")}
        required_not_null = {
            "id",
            "purpose",
            "channel",
            "subject_hash",
            "status",
            "failed_attempts",
            "send_count",
            "expires_at",
            "resend_available_at",
            "request_ip_hash",
            "delivery_status",
            "created_at",
        }
        primary_key = set(inspector.get_pk_constraint("auth_challenges")["constrained_columns"])
        foreign_keys = inspector.get_foreign_keys("auth_challenges")
        has_user_fk = any(
            fk["constrained_columns"] == ["user_id"]
            and fk["referred_table"] == "users"
            and fk["referred_columns"] == ["id"]
            for fk in foreign_keys
        )
        if (
            set(columns) != expected_columns
            or any(columns[name]["nullable"] for name in required_not_null)
            or primary_key != {"id"}
            or not has_user_fk
        ):
            raise RuntimeError(
                "Existing auth_challenges table does not match the P0-020 contract"
            )
    else:
        op.create_table(
            "auth_challenges",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("purpose", sa.String(50), nullable=False),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("subject_hash", sa.String(64), nullable=False),
            sa.Column("contact_hash", sa.String(64), nullable=True),
            sa.Column("otp_hash", sa.String(64), nullable=True),
            sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
            sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("send_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("authorization_hash", sa.String(64), nullable=True),
            sa.Column("authorization_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("authorization_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("request_ip_hash", sa.String(64), nullable=False),
            sa.Column("delivery_status", sa.String(24), nullable=False, server_default="PENDING"),
            sa.Column("failure_reason", sa.String(255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_challenges_user_id ON auth_challenges (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_challenges_purpose ON auth_challenges (purpose)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_challenges_subject_hash ON auth_challenges (subject_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_auth_challenges_request_ip_hash "
        "ON auth_challenges (request_ip_hash)"
    )


def downgrade():
    op.drop_index("ix_auth_challenges_request_ip_hash", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_subject_hash", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_purpose", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_user_id", table_name="auth_challenges")
    op.drop_table("auth_challenges")
    op.execute("DROP INDEX IF EXISTS uq_users_employee_code_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_roll_number_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_mobile_number")
    op.execute("DROP INDEX IF EXISTS uq_users_email_normalized")
    op.drop_constraint("ck_users_account_status", "users", type_="check")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "session_version")
    op.drop_column("users", "account_status")
    op.drop_column("users", "mobile_is_personal")
    op.drop_column("users", "mobile_verified")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "mobile_number")
    op.drop_column("users", "institutional_mobile")
    op.drop_column("users", "institutional_email")
