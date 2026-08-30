"""Pilot governance mode and draft-subject academic weightages.

Revision ID: 20260830_p031_pilot_weights
Revises: 20260830_p030_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "20260830_p031_pilot_weights"
down_revision = "20260830_p030_governance"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    course_columns = {column["name"] for column in inspector.get_columns("courses")}
    if "governance_mode" not in course_columns:
        op.add_column("courses", sa.Column("governance_mode", sa.String(24), nullable=False, server_default="INSTITUTIONAL"))
        op.create_index("ix_courses_governance_mode", "courses", ["governance_mode"])

    review_columns = {column["name"] for column in inspector.get_columns("syllabus_subject_reviews")}
    syllabus_review_columns = {column["name"] for column in inspector.get_columns("syllabus_reviews")}
    if "draft_subject_weightages" not in syllabus_review_columns:
        op.add_column("syllabus_reviews", sa.Column("draft_subject_weightages", sa.JSON(), nullable=False, server_default="{}"))
    additions = (
        ("draft_weightages", sa.JSON(), "{}"),
        ("weightage_status", sa.String(24), "NOT_CONFIGURED"),
        ("weightage_version", sa.Integer(), "0"),
        ("weightage_recommendation_comment", sa.String(2000), ""),
        ("weightage_recommended_at", sa.DateTime(timezone=True), None),
        ("weightage_approved_at", sa.DateTime(timezone=True), None),
        ("weightage_approved_by", sa.Integer(), None),
    )
    for name, kind, default in additions:
        if name not in review_columns:
            op.add_column("syllabus_subject_reviews", sa.Column(name, kind, nullable=default is None,
                server_default=default))
    # The final approver remains an auditable user reference.
    foreign_keys = {fk.get("name") for fk in sa.inspect(bind).get_foreign_keys("syllabus_subject_reviews")}
    if "fk_subject_review_weightage_approved_by" not in foreign_keys:
        op.create_foreign_key("fk_subject_review_weightage_approved_by", "syllabus_subject_reviews", "users",
            ["weightage_approved_by"], ["id"])


def downgrade():
    raise RuntimeError("Pilot governance evidence is retained; restore a verified backup to roll back.")
