"""Add syllabus units and attach existing topics safely.

Revision ID: 20260823_p023_units
Revises: d8027c4ad5d1
"""

from alembic import op
import sqlalchemy as sa

revision = "20260823_p023_units"
down_revision = "d8027c4ad5d1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("subjects_name_key", "subjects", type_="unique")
    op.create_unique_constraint("uq_subjects_course_name", "subjects", ["course_id", "name"])
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subject_id", "name", name="uq_units_subject_name"),
    )
    op.create_index("ix_units_subject_id", "units", ["subject_id"])
    op.add_column("topics", sa.Column("unit_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_topics_unit_id", "topics", "units", ["unit_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_topics_unit_id", "topics", ["unit_id"])

    connection = op.get_bind()
    subjects = connection.execute(sa.text("SELECT DISTINCT subject_id FROM topics ORDER BY subject_id")).fetchall()
    for (subject_id,) in subjects:
        unit_id = connection.execute(
            sa.text("INSERT INTO units (subject_id, name, description, sequence) VALUES (:subject_id, 'General', 'Automatically created for syllabus topics that existed before Unit-level organization.', 1) RETURNING id"),
            {"subject_id": subject_id},
        ).scalar_one()
        connection.execute(sa.text("UPDATE topics SET unit_id = :unit_id WHERE subject_id = :subject_id"), {"unit_id": unit_id, "subject_id": subject_id})

def downgrade():
    op.drop_index("ix_topics_unit_id", table_name="topics")
    op.drop_constraint("fk_topics_unit_id", "topics", type_="foreignkey")
    op.drop_column("topics", "unit_id")
    op.drop_index("ix_units_subject_id", table_name="units")
    op.drop_table("units")
    op.drop_constraint("uq_subjects_course_name", "subjects", type_="unique")
    op.create_unique_constraint("subjects_name_key", "subjects", ["name"])
