"""Course Knowledge Studio and versioned delivery policy.

Revision ID: 20260916_p0362a_studio
Revises: 20260913_p036_content
"""
from alembic import op
import sqlalchemy as sa

revision = "20260916_p0362a_studio"
down_revision = "20260913_p036_content"
branch_labels = depends_on = None


def upgrade():
    op.create_table("course_teaching_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en-IN"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_revision", sa.Integer()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("activated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("course_id", "language", name="uq_course_teaching_pack_language"))
    op.create_index("ix_course_teaching_packs_course_id", "course_teaching_packs", ["course_id"])
    op.create_index("ix_course_teaching_packs_status", "course_teaching_packs", ["status"])

    op.create_table("course_teaching_pack_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("teaching_pack_id", sa.Integer(), sa.ForeignKey("course_teaching_packs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("course_policy", sa.JSON(), nullable=False),
        sa.Column("validation_report", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("revision_notes", sa.String(1000)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("activated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("teaching_pack_id", "revision", name="uq_course_teaching_pack_revision"))
    op.create_index("ix_course_teaching_pack_revisions_teaching_pack_id", "course_teaching_pack_revisions", ["teaching_pack_id"])
    op.create_index("ix_course_teaching_pack_revisions_status", "course_teaching_pack_revisions", ["status"])
    op.create_index("ix_course_teaching_pack_revisions_content_hash", "course_teaching_pack_revisions", ["content_hash"])


def downgrade():
    raise RuntimeError("Course teaching-pack evidence is retained; restore a verified backup to roll back.")
