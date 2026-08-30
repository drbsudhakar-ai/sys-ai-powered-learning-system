"""Phase 4 academic-weightage structure, permissions, and migration regression checks."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AcademicWeightageTests(unittest.TestCase):
    def test_migration_extends_phase_two_without_replacing_existing_weightages(self):
        source = (ROOT / "alembic" / "versions" / "20260824_p024_phase4_academic_weightages.py").read_text(encoding="utf-8")
        self.assertIn('down_revision = "20260823_p023_units"', source)
        self.assertIn('"unit_weightages"', source)
        self.assertIn('"subtopic_weightages"', source)
        self.assertNotIn('drop_table("subject_weightages")', source)
        self.assertNotIn('drop_table("topic_weightages")', source)

    def test_new_levels_have_parent_scope_uniqueness_and_valid_percentage_constraints(self):
        source = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
        self.assertIn('class UnitWeightage(Base):', source)
        self.assertIn('class SubtopicWeightage(Base):', source)
        self.assertIn('name="uq_subject_unit_weight"', source)
        self.assertIn('name="uq_topic_subtopic_weight"', source)
        self.assertIn('name="ck_unit_weight_percent"', source)
        self.assertIn('name="ck_subtopic_weight_percent"', source)

    def test_subject_experts_are_limited_to_assigned_subjects(self):
        source = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        self.assertIn('_academic_staff = require_roles("admin", "faculty")', source)
        self.assertIn('Academic responsibility for this course is required', source)
        self.assertIn('Only a course coordinator or administrator can edit subject weightages', source)
        self.assertIn('Subject expert responsibility is required for this subject', source)

    def test_every_group_requires_all_siblings_unique_items_and_exact_total(self):
        source = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        self.assertIn('Each syllabus item can appear only once', source)
        self.assertIn('Weightages must total exactly 100%', source)
        self.assertIn('Weightages must include every item', source)
        self.assertIn('action=f"weightage.{payload.level}.update"', source)

    def test_payload_validates_all_four_levels_and_percentage_bounds(self):
        source = (ROOT / "app" / "schemas.py").read_text(encoding="utf-8")
        self.assertIn('Literal["subject", "unit", "topic", "subtopic"]', source)
        self.assertIn('weight_percent: float = Field(..., ge=0, le=100, allow_inf_nan=False)', source)


if __name__ == "__main__":
    unittest.main()
