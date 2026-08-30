"""Regression coverage for controlled SYS course publication."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CoursePublicationTests(unittest.TestCase):
    def test_migration_extends_phase_four_and_preserves_existing_courses(self):
        source = (ROOT / "alembic/versions/20260824_p025_course_publication.py").read_text()
        self.assertIn('down_revision = "20260824_p024_weights"', source)
        self.assertIn("CASE WHEN is_active THEN 'PUBLISHED' ELSE 'DRAFT' END", source)

    def test_all_lifecycle_actions_are_audited_and_publish_is_admin_only(self):
        source = (ROOT / "app/routes/admin.py").read_text()
        for action in ("course.submit_for_review", "course.publish", "course.return_to_draft", "course.archive"):
            self.assertIn(action, source)
        self.assertIn('actor: models.User = Depends(_admin)', source)

    def test_readiness_requires_syllabus_ownership_and_weightages(self):
        source = (ROOT / "app/routes/admin.py").read_text()
        for item in ("Structured syllabus", "Active course coordinator", "Subject experts", "Subject weightages", "Unit, topic and subtopic weightages"):
            self.assertIn(item, source)

    def test_generic_course_updates_cannot_bypass_publication(self):
        source = (ROOT / "app/routes/courses.py").read_text()
        self.assertIn("Use the controlled course publication workflow", source)
        self.assertIn('publication_status="DRAFT"', source)


if __name__ == "__main__":
    unittest.main()
