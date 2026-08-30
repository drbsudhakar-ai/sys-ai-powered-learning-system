"""Subject review assignments and exact-version publication stamps."""
from alembic import op
import sqlalchemy as sa

revision = "20260828_p029_subject_review"
down_revision = "20260828_p028_syllabus"
branch_labels = depends_on = None

def upgrade():
    op.add_column("syllabus_revisions", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table("syllabus_subject_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("syllabus_reviews.id"), nullable=False),
        sa.Column("subject_key", sa.String(90), nullable=False),
        sa.Column("live_subject_id", sa.Integer(), sa.ForeignKey("subjects.id")),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_nodes", sa.JSON(), nullable=False),
        sa.Column("proposed_nodes", sa.JSON(), nullable=False),
        sa.Column("comment", sa.String(2000), nullable=False),
        sa.Column("decision_comment", sa.String(2000), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True)),
        sa.Column("recommended_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("review_id", "subject_key", name="uq_subject_review_branch"))
    op.create_index("ix_syllabus_subject_reviews_review_id", "syllabus_subject_reviews", ["review_id"])
    # Preserve legacy proposal contents but route unfinished work through explicit subject requests.
    op.execute("UPDATE syllabus_reviews SET status = 'CANCELLED' WHERE subject_id IS NOT NULL AND status IN ('DRAFT', 'SUBMITTED', 'CHANGES_REQUESTED')")
    op.execute("UPDATE syllabus_reviews SET status = 'DRAFT' WHERE subject_id IS NULL AND status = 'SUBMITTED'")
    # Only an existing current revision with an explicit course publication is stamped.
    op.execute("UPDATE syllabus_revisions SET published_at = (SELECT published_at FROM courses WHERE courses.id = syllabus_revisions.course_id) WHERE EXISTS (SELECT 1 FROM courses WHERE courses.id = syllabus_revisions.course_id AND courses.publication_status = 'PUBLISHED' AND courses.syllabus_revision = syllabus_revisions.number AND courses.published_at >= syllabus_revisions.created_at)")

def downgrade():
    raise RuntimeError("Review and publication history is retained; restore a verified backup to roll back.")
