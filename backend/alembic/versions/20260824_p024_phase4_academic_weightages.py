"""Add unit and subtopic academic weightage persistence.

Revision ID: 20260824_p024_weights
Revises: 20260823_p023_units
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_p024_weights"
down_revision = "20260823_p023_units"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "unit_weightages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_percent", sa.Float(), nullable=False),
        sa.UniqueConstraint("subject_id", "unit_id", name="uq_subject_unit_weight"),
        sa.CheckConstraint("weight_percent >= 0 AND weight_percent <= 100", name="ck_unit_weight_percent"),
    )
    op.create_index("ix_unit_weightages_subject_id", "unit_weightages", ["subject_id"])
    op.create_index("ix_unit_weightages_unit_id", "unit_weightages", ["unit_id"])

    op.create_table(
        "subtopic_weightages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subtopic_id", sa.Integer(), sa.ForeignKey("subtopics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_percent", sa.Float(), nullable=False),
        sa.UniqueConstraint("topic_id", "subtopic_id", name="uq_topic_subtopic_weight"),
        sa.CheckConstraint("weight_percent >= 0 AND weight_percent <= 100", name="ck_subtopic_weight_percent"),
    )
    op.create_index("ix_subtopic_weightages_topic_id", "subtopic_weightages", ["topic_id"])
    op.create_index("ix_subtopic_weightages_subtopic_id", "subtopic_weightages", ["subtopic_id"])


def downgrade():
    op.drop_index("ix_subtopic_weightages_subtopic_id", table_name="subtopic_weightages")
    op.drop_index("ix_subtopic_weightages_topic_id", table_name="subtopic_weightages")
    op.drop_table("subtopic_weightages")
    op.drop_index("ix_unit_weightages_unit_id", table_name="unit_weightages")
    op.drop_index("ix_unit_weightages_subject_id", table_name="unit_weightages")
    op.drop_table("unit_weightages")
