"""Focused structural checks for Phase 3 administrator academic ownership."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AcademicOwnershipTests(unittest.TestCase):
    def test_existing_assignment_models_are_reused_without_duplicate_tables(self):
        models = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
        self.assertIn('class FacultyCourseAssignment(Base):', models)
        self.assertIn('class SubjectExpertAssignment(Base):', models)
        self.assertIn('uq_faculty_course_coordinator', models)
        self.assertIn('uq_faculty_subject_expert', models)

    def test_all_assignment_actions_have_administrator_audit_events(self):
        routes = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        for action in ("faculty.assign_course_coordinator", "faculty.remove_course_coordinator", "faculty.assign_subject_expert", "faculty.remove_subject_expert"):
            self.assertIn(f'action="{action}"', routes)
        self.assertIn("current_admin: models.User = Depends(_admin)", routes)

    def test_inactive_faculty_and_duplicate_assignments_are_rejected(self):
        routes = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(routes.count('detail="Faculty account is inactive"'), 2)
        self.assertIn('detail="Course Coordinator assignment already exists"', routes)
        self.assertIn('detail="Subject Expert assignment already exists"', routes)

    def test_subject_expert_payload_includes_course_context(self):
        routes = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        schemas = (ROOT / "app" / "schemas.py").read_text(encoding="utf-8")
        self.assertIn("course_id=row.subject.course_id", routes)
        self.assertIn("course_title=row.subject.course.title", routes)
        self.assertIn("course_title: Optional[str] = None", schemas)


if __name__ == "__main__":
    unittest.main()
