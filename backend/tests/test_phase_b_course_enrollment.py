"""Contract checks for published course enrollment and scoped workspaces."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PhaseBCourseEnrollmentTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_enrollment_requires_student_and_published_course(self):
        routes = self.read("backend/app/routes/courses.py")
        self.assertIn('@router.post("/{course_id}/enroll"', routes)
        self.assertIn('Depends(require_roles("student"))', routes)
        self.assertIn('course.publication_status != "PUBLISHED"', routes)

    def test_duplicate_enrollment_is_rejected_and_audited(self):
        routes = self.read("backend/app/routes/courses.py")
        self.assertIn('status_code=409, detail="You are already enrolled', routes)
        self.assertIn('action="course.student_enrolled"', routes)

    def test_workspace_enforces_student_and_faculty_scope(self):
        routes = self.read("backend/app/routes/courses.py")
        self.assertIn('models.StudentCourseEnrollment.student_id == current_user.id', routes)
        self.assertIn('models.FacultyCourseAssignment.faculty_id == current_user.id', routes)
        self.assertIn('models.SubjectExpertAssignment.faculty_id == current_user.id', routes)
        self.assertIn('subject.id not in allowed_subject_ids', routes)

    def test_workspace_contains_complete_syllabus_and_learning_sections(self):
        page = self.read("frontend/pages/courses/[id]/workspace.js")
        for section in ("Subject → Unit → Topic → Subtopic", "Assessments", "Remedial learning", "Mastery practice", "Course materials"):
            self.assertIn(section, page)


if __name__ == "__main__":
    unittest.main()
