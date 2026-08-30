"""Separate syllabus approval, weightage approval, and coordinator readiness.

Revision ID: 20260830_p030_governance
Revises: 20260828_p029_subject_review
"""
from alembic import op
import sqlalchemy as sa

revision = "20260830_p030_governance"
down_revision = "20260828_p029_subject_review"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    course_columns = {column["name"] for column in inspector.get_columns("courses")}
    if "coordinator_readiness_status" not in course_columns:
        op.add_column("courses", sa.Column("coordinator_readiness_status", sa.String(24), nullable=False, server_default="PENDING"))
    if "coordinator_confirmed_at" not in course_columns:
        op.add_column("courses", sa.Column("coordinator_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    if "coordinator_confirmed_by" not in course_columns:
        op.add_column("courses", sa.Column("coordinator_confirmed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))

    if "subject_weightage_approvals" not in inspector.get_table_names():
        op.create_table(
            "subject_weightage_approvals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("snapshot_hash", sa.String(64), nullable=False, server_default=""),
            sa.Column("recommendation_comment", sa.String(2000), nullable=False, server_default=""),
            sa.Column("recommended_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("recommended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decision_comment", sa.String(2000), nullable=False, server_default=""),
            sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("course_id", "subject_id", name="uq_subject_weightage_approval"),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("subject_weightage_approvals")}
    for name, columns in (
        ("ix_subject_weightage_approvals_course_id", ["course_id"]),
        ("ix_subject_weightage_approvals_subject_id", ["subject_id"]),
        ("ix_subject_weightage_approvals_status", ["status"]),
    ):
        if name not in indexes:
            op.create_index(name, "subject_weightage_approvals", columns)


def downgrade():
    raise RuntimeError("Academic approval history is retained; restore a verified backup to roll back.")
