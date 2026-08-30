"""Contract checks for Phase C course-to-classroom integration."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PhaseCAILearningContractTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_topic_launch_requires_student_and_published_enrollment(self):
        routes = self.read("backend/app/routes/courses.py")
        service = self.read("backend/app/services/course_learning.py")
        self.assertIn('@router.post("/{course_id}/learning/topics/{topic_id}/launch")', routes)
        self.assertIn('Depends(require_roles("student"))', routes)
        self.assertIn('course.publication_status != "PUBLISHED"', service)
        self.assertIn("StudentCourseEnrollment.student_id == student.id", service)

    def test_topic_is_validated_inside_the_requested_course(self):
        service = self.read("backend/app/services/course_learning.py")
        self.assertIn("subject.course_id != course_id", service)
        self.assertIn("subtopic.topic_id != topic.id", service)

    def test_launch_reuses_open_individual_session_and_records_evidence(self):
        service = self.read("backend/app/services/course_learning.py")
        self.assertIn('models.LearningSession.mode == "INDIVIDUAL"', service)
        self.assertIn("OPEN_SESSION_STATUSES", service)
        self.assertIn('event_type="SESSION_STARTED"', service)
        self.assertIn('"reused": reused', service)

    def test_facilitator_comes_from_academic_ownership(self):
        service = self.read("backend/app/services/course_learning.py")
        self.assertIn("models.SubjectExpertAssignment", service)
        self.assertIn("models.FacultyCourseAssignment", service)
        self.assertIn("created_by=facilitator_id", service)

    def test_workspace_and_classroom_expose_phase_c_controls(self):
        workspace = self.read("frontend/pages/courses/[id]/workspace.js")
        classroom = self.read("frontend/pages/learning-sessions/[id]/lecture.js")
        for label in ("Start AI lesson", "Resume AI lesson", "AI learning sessions"):
            self.assertIn(label, workspace)
        for label in ("TEACHING JOURNEY", "AskLecturerPanel", "LectureControls", "Course workspace"):
            self.assertIn(label, classroom)


if __name__ == "__main__":
    unittest.main()
