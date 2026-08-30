"""Controlled course publication lifecycle."""
from alembic import op
import sqlalchemy as sa

revision = "20260824_p025_publish"
down_revision = "20260824_p024_weights"
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("courses")}
    if "publication_status" not in existing:
        op.add_column("courses", sa.Column("publication_status", sa.String(32), nullable=False, server_default="DRAFT"))
    for name in ("submitted_for_review_at", "published_at", "archived_at"):
        if name not in existing:
            op.add_column("courses", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    for name in ("submitted_for_review_by", "published_by", "archived_by"):
        if name not in existing:
            op.add_column("courses", sa.Column(name, sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("courses")}
    if "ix_courses_publication_status" not in indexes:
        op.create_index("ix_courses_publication_status", "courses", ["publication_status"])
    op.execute("UPDATE courses SET publication_status = CASE WHEN is_active THEN 'PUBLISHED' ELSE 'DRAFT' END WHERE publication_status IS NULL OR publication_status = 'DRAFT'")
    op.alter_column("courses", "is_active", server_default=sa.false())

def downgrade():
    op.drop_index("ix_courses_publication_status", table_name="courses")
    for name in ("archived_by", "published_by", "submitted_for_review_by", "archived_at", "published_at", "submitted_for_review_at", "publication_status"):
        op.drop_column("courses", name)
    op.alter_column("courses", "is_active", server_default=sa.true())
