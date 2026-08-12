"""P0-011 Student assessment attempt / evaluation / answer key

Revision ID: 20260812_p011_attempts
Revises: 20260812_p010_question_intel
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p011_attempts"
down_revision = "20260812_p010_question_intel"
branch_labels = None
depends_on = None


def upgrade():
    for stmt in [
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS available_from TIMESTAMPTZ",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS available_until TIMESTAMPTZ",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS answer_key_released BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS stem_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS options_snapshot JSONB",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS correct_answer_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS explanation_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS question_type_snapshot VARCHAR(50)",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS shortcut_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS alternative_solution_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS common_traps_snapshot TEXT",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS negative_marks_snapshot DOUBLE PRECISION",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS subject_name_snapshot VARCHAR(200)",
        "ALTER TABLE assessment_questions ADD COLUMN IF NOT EXISTS topic_name_snapshot VARCHAR(200)",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS auto_submitted BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS time_spent_seconds DOUBLE PRECISION",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS percentage DOUBLE PRECISION",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS correct_count INTEGER",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS incorrect_count INTEGER",
        "ALTER TABLE assessment_attempts ADD COLUMN IF NOT EXISTS unanswered_count INTEGER",
        "ALTER TABLE assessment_attempts ALTER COLUMN submitted_at DROP NOT NULL",
        "ALTER TABLE assessment_attempts ALTER COLUMN submitted_at DROP DEFAULT",
    ]:
        op.execute(stmt)

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attempt_responses (
            id SERIAL PRIMARY KEY,
            attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
            assessment_question_id INTEGER NOT NULL REFERENCES assessment_questions(id),
            question_id INTEGER NOT NULL REFERENCES questions(id),
            question_sequence INTEGER NOT NULL DEFAULT 1,
            selected_answer TEXT,
            answered BOOLEAN NOT NULL DEFAULT FALSE,
            marked_for_review BOOLEAN NOT NULL DEFAULT FALSE,
            time_spent_seconds DOUBLE PRECISION DEFAULT 0,
            submitted_answer_snapshot TEXT,
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_attempt_aq UNIQUE (attempt_id, assessment_question_id)
        )
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS attempt_responses CASCADE")
    for col in [
        "expires_at",
        "auto_submitted",
        "time_spent_seconds",
        "percentage",
        "correct_count",
        "incorrect_count",
        "unanswered_count",
    ]:
        op.execute(f"ALTER TABLE assessment_attempts DROP COLUMN IF EXISTS {col}")
    for col in [
        "stem_snapshot",
        "options_snapshot",
        "correct_answer_snapshot",
        "explanation_snapshot",
        "question_type_snapshot",
        "shortcut_snapshot",
        "alternative_solution_snapshot",
        "common_traps_snapshot",
        "negative_marks_snapshot",
        "subject_name_snapshot",
        "topic_name_snapshot",
    ]:
        op.execute(f"ALTER TABLE assessment_questions DROP COLUMN IF EXISTS {col}")
    for col in ["available_from", "available_until", "max_attempts", "answer_key_released"]:
        op.execute(f"ALTER TABLE assessments DROP COLUMN IF EXISTS {col}")
