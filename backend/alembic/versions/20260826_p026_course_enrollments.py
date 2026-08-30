"""Professional course enrollment lifecycle and self-enrollment control."""
from alembic import op
import sqlalchemy as sa

revision = "20260826_p026_enrollment"
down_revision = "20260824_p025_publish"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("courses", sa.Column("self_enrollment_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("student_course_enrollments", sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"))
    op.add_column("student_course_enrollments", sa.Column("enrollment_source", sa.String(24), nullable=False, server_default="ADMIN"))
    op.add_column("student_course_enrollments", sa.Column("enrolled_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("student_course_enrollments", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.create_index("ix_student_course_enrollments_status", "student_course_enrollments", ["status"])


def downgrade():
    op.drop_index("ix_student_course_enrollments_status", table_name="student_course_enrollments")
    for name in ("updated_at", "enrolled_by", "enrollment_source", "status"):
        op.drop_column("student_course_enrollments", name)
    op.drop_column("courses", "self_enrollment_enabled")
