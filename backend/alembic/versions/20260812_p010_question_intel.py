"""P0-010 Question Knowledge Base & Intelligence

Revision ID: 20260812_p010_question_intel
Revises: 20260812_p009_assessment_engine
Create Date: 2026-08-12
"""

from alembic import op

revision = "20260812_p010_question_intel"
down_revision = "20260812_p009_assessment_engine"
branch_labels = None
depends_on = None


def upgrade():
    for stmt in [
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS options JSONB",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS correct_answer TEXT",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS explanation TEXT",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS marks DOUBLE PRECISION DEFAULT 1",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS negative_marks DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS source VARCHAR(100)",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS source_year INTEGER",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS exam_name VARCHAR(200)",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS concept_tags JSONB",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS learning_objective VARCHAR(500)",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS shortcut TEXT",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS alternative_solution TEXT",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS common_traps TEXT",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS estimated_time_seconds INTEGER",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS similarity_fingerprint VARCHAR(64)",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS novelty_class VARCHAR(30) DEFAULT 'NOVEL'",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    ]:
        op.execute(stmt)
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_similarity_fingerprint ON questions (similarity_fingerprint)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_exam_papers (
            id SERIAL PRIMARY KEY,
            exam_name VARCHAR(200) NOT NULL,
            exam_year INTEGER NOT NULL,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            exam_type VARCHAR(100),
            source VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_exam_questions (
            id SERIAL PRIMARY KEY,
            paper_id INTEGER NOT NULL REFERENCES historical_exam_papers(id) ON DELETE CASCADE,
            subject_id INTEGER REFERENCES subjects(id),
            topic_id INTEGER REFERENCES topics(id),
            subtopic_id INTEGER REFERENCES subtopics(id),
            question_text TEXT NOT NULL,
            question_type VARCHAR(50),
            marks DOUBLE PRECISION,
            difficulty VARCHAR(20),
            concept_tags JSONB,
            linked_question_id INTEGER REFERENCES questions(id),
            similarity_class VARCHAR(30) DEFAULT 'CONCEPT_VARIANT',
            fingerprint VARCHAR(64)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hist_q_fingerprint ON historical_exam_questions (fingerprint)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_weightages (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            weight_percent DOUBLE PRECISION NOT NULL,
            CONSTRAINT uq_course_subject_weight UNIQUE (course_id, subject_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_weightages (
            id SERIAL PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            weight_percent DOUBLE PRECISION NOT NULL,
            syllabus_importance DOUBLE PRECISION DEFAULT 0.5,
            CONSTRAINT uq_subject_topic_weight UNIQUE (subject_id, topic_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS priority_weight_configs (
            id SERIAL PRIMARY KEY,
            course_id INTEGER UNIQUE REFERENCES courses(id),
            w_historical_weightage DOUBLE PRECISION NOT NULL DEFAULT 0.25,
            w_historical_frequency DOUBLE PRECISION NOT NULL DEFAULT 0.25,
            w_concept_frequency DOUBLE PRECISION NOT NULL DEFAULT 0.15,
            w_recent_trend DOUBLE PRECISION NOT NULL DEFAULT 0.15,
            w_syllabus_importance DOUBLE PRECISION NOT NULL DEFAULT 0.10,
            w_exam_pattern DOUBLE PRECISION NOT NULL DEFAULT 0.10
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_intelligence_snapshots (
            id SERIAL PRIMARY KEY,
            topic_id INTEGER NOT NULL REFERENCES topics(id),
            course_id INTEGER NOT NULL REFERENCES courses(id),
            historical_frequency DOUBLE PRECISION,
            avg_marks_weightage DOUBLE PRECISION,
            recent_trend VARCHAR(20),
            priority_score DOUBLE PRECISION,
            priority_label VARCHAR(20),
            contributing_factors JSONB,
            question_count INTEGER DEFAULT 0,
            frequently_tested_concepts JSONB,
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_topic_course_intel UNIQUE (topic_id, course_id)
        )
        """
    )


def downgrade():
    for table in [
        "topic_intelligence_snapshots",
        "priority_weight_configs",
        "topic_weightages",
        "subject_weightages",
        "historical_exam_questions",
        "historical_exam_papers",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for col in [
        "options",
        "correct_answer",
        "explanation",
        "marks",
        "negative_marks",
        "source",
        "source_year",
        "exam_name",
        "concept_tags",
        "learning_objective",
        "shortcut",
        "alternative_solution",
        "common_traps",
        "estimated_time_seconds",
        "quality_score",
        "similarity_fingerprint",
        "novelty_class",
        "updated_at",
    ]:
        op.execute(f"ALTER TABLE questions DROP COLUMN IF EXISTS {col}")
