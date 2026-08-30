"""Static safety checks for the additive syllabus hierarchy and migration."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CourseSyllabusStructureTests(unittest.TestCase):
    def test_migration_extends_the_confirmed_database_head(self):
        migration = (ROOT / "alembic" / "versions" / "20260823_p023_phase2_units.py").read_text(encoding="utf-8")
        self.assertIn('down_revision = "d8027c4ad5d1"', migration)
        self.assertIn('"units"', migration)
        self.assertIn('"unit_id"', migration)

    def test_existing_topics_are_backfilled_without_replacing_identifiers(self):
        migration = (ROOT / "alembic" / "versions" / "20260823_p023_phase2_units.py").read_text(encoding="utf-8")
        self.assertIn("SELECT DISTINCT subject_id FROM topics", migration)
        self.assertIn("UPDATE topics SET unit_id", migration)
        self.assertNotIn("DELETE FROM topics", migration)

    def test_subject_names_are_unique_within_each_course(self):
        models = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
        self.assertIn('UniqueConstraint("course_id", "name", name="uq_subjects_course_name")', models)

    def test_legacy_topic_creation_remains_compatible(self):
        curriculum = (ROOT / "app" / "routes" / "curriculum.py").read_text(encoding="utf-8")
        self.assertIn('name="General"', curriculum)
        self.assertIn("unit_id=unit.id", curriculum)

    def test_syllabus_endpoints_require_administrator_authorization(self):
        admin = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        self.assertIn('/courses/{course_id}/syllabus/import', admin)
        self.assertIn("Depends(_admin)", admin)


if __name__ == "__main__":
    unittest.main()
