"""Versioned syllabus review and immutable approved snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "20260828_p028_syllabus"
down_revision = "20260827_p027_ai_gateway"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for table, name, kind, default in (
        ("courses", "syllabus_revision", sa.Integer(), "0"),
        ("subjects", "sequence", sa.Integer(), "1"),
        ("topics", "sequence", sa.Integer(), "1"),
        ("subtopics", "sequence", sa.Integer(), "1"),
        ("units", "learning_outcome", sa.String(500), None),
    ):
        if name not in {c["name"] for c in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, sa.Column(name, kind, nullable=default is None, server_default=default))
    if "syllabus_reviews" not in sa.inspect(bind).get_table_names():
        op.create_table("syllabus_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id")),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("base_revision", sa.Integer(), nullable=False),
            sa.Column("base_hash", sa.String(64), nullable=False),
            sa.Column("base_nodes", sa.JSON(), nullable=False),
            sa.Column("proposed_nodes", sa.JSON(), nullable=False),
            sa.Column("summary", sa.String(1000), nullable=False),
            sa.Column("decision_comment", sa.String(2000), nullable=False),
            sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("decided_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("submitted_at", sa.DateTime(timezone=True)))
        op.create_index("ix_syllabus_reviews_course_id", "syllabus_reviews", ["course_id"])
    if "syllabus_revisions" not in sa.inspect(bind).get_table_names():
        op.create_table("syllabus_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("nodes", sa.JSON(), nullable=False),
            sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("syllabus_reviews.id"), nullable=False),
            sa.Column("summary", sa.String(1000), nullable=False),
            sa.Column("course_title", sa.String(200), nullable=False),
            sa.Column("programme_code", sa.String(80)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("course_id", "number", name="uq_syllabus_revision"))
        op.create_index("ix_syllabus_revisions_course_id", "syllabus_revisions", ["course_id"])


def downgrade():
    # Keep academic history until an operator explicitly exports and authorizes removal.
    raise RuntimeError("Syllabus review history is retained. Restore a verified backup to roll back.")
