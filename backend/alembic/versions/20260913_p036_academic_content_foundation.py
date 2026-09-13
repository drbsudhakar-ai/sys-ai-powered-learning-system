"""Professor-grade academic content foundation.

Revision ID: 20260913_p036_content
Revises: 20260830_p031_pilot_weights
"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_p036_content"
down_revision = "20260830_p031_pilot_weights"
branch_labels = depends_on = None


def upgrade():
    op.create_table("academic_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE")),
        sa.Column("source_code", sa.String(80), nullable=False), sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False), sa.Column("issuing_authority", sa.String(240)),
        sa.Column("publication_date", sa.DateTime(timezone=True)), sa.Column("canonical_url", sa.String(1000)),
        sa.Column("rights_classification", sa.String(40), nullable=False, server_default="REFERENCE_ONLY"),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("verified_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("course_id", "source_code", name="uq_academic_source_course_code"))
    op.create_index("ix_academic_sources_course_id", "academic_sources", ["course_id"])
    op.create_index("ix_academic_sources_subject_id", "academic_sources", ["subject_id"])
    op.create_index("ix_academic_sources_verification_status", "academic_sources", ["verification_status"])

    op.create_table("academic_source_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("academic_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False), sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("notes", sa.String(1000)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_id", "revision", name="uq_academic_source_revision"))
    op.create_index("ix_academic_source_revisions_source_id", "academic_source_revisions", ["source_id"])
    op.create_index("ix_academic_source_revisions_content_hash", "academic_source_revisions", ["content_hash"])

    op.create_table("topic_knowledge_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en-IN"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("topic_id", "language", name="uq_topic_knowledge_language"))
    op.create_index("ix_topic_knowledge_packages_topic_id", "topic_knowledge_packages", ["topic_id"])
    op.create_index("ix_topic_knowledge_packages_status", "topic_knowledge_packages", ["status"])

    op.create_table("topic_knowledge_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("topic_knowledge_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *[sa.Column(name, sa.JSON(), nullable=False) for name in ("objectives", "prerequisites", "concepts", "definitions", "formulas", "verified_facts", "worked_examples", "misconceptions", "exam_relevance", "subtopic_coverage", "source_revision_ids")],
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("package_id", "revision", name="uq_topic_knowledge_revision"))
    op.create_index("ix_topic_knowledge_revisions_package_id", "topic_knowledge_revisions", ["package_id"])
    op.create_index("ix_topic_knowledge_revisions_content_hash", "topic_knowledge_revisions", ["content_hash"])

    op.create_table("subject_professor_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en-IN"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        *[sa.Column(name, sa.JSON(), nullable=False) for name in ("teaching_strategy", "required_stage_types", "example_rules", "narration_rules", "visual_rules", "assessment_rules", "accuracy_constraints")],
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("subject_id", "language", name="uq_subject_professor_language"))
    op.create_index("ix_subject_professor_profiles_subject_id", "subject_professor_profiles", ["subject_id"])
    op.create_index("ix_subject_professor_profiles_status", "subject_professor_profiles", ["status"])

    op.create_table("topic_academic_reviewer_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("topic_id", "faculty_id", name="uq_topic_academic_reviewer"))
    op.create_index("ix_topic_academic_reviewer_assignments_topic_id", "topic_academic_reviewer_assignments", ["topic_id"])
    op.create_index("ix_topic_academic_reviewer_assignments_faculty_id", "topic_academic_reviewer_assignments", ["faculty_id"])


def downgrade():
    raise RuntimeError("Academic evidence is retained; restore a verified backup to roll back.")
