"""Real branded course/subject PDF generation and ownership-scope regression checks."""

from datetime import datetime, timezone
from pathlib import Path
import unittest

from app.services.course_profile_pdf import build_coordinator_courses_pdf, build_course_profile_pdf, build_subject_expert_assignments_pdf


ROOT = Path(__file__).resolve().parents[1]


def report_payload(subject_scope=False, large=False):
    physics = {"id": 10, "name": "Physics", "weight_percent": 25, "units": [{"id": 20, "name": "Mechanics", "sequence": 1, "weight_percent": 60, "topics": [{"id": 30, "name": "Kinematics", "weight_percent": 70, "subtopics": [{"id": 40, "name": "Motion", "weight_percent": 60}, {"id": 41, "name": "Velocity", "weight_percent": 40}]}]}]}
    chemistry = {"id": 11, "name": "Chemistry", "weight_percent": 25, "units": [{"id": 21, "name": "Organic Chemistry", "sequence": 1, "weight_percent": 100, "topics": []}]}
    if large:
        physics["units"][0]["topics"] = [{"id": 100 + index, "name": f"Physics topic {index}", "weight_percent": 2, "subtopics": [{"id": 1000 + index, "name": f"Concept {index}", "weight_percent": 100}]} for index in range(55)]
    subjects = [physics] if subject_scope else [physics, chemistry]
    return {"course": {"id": 1, "title": "NEET Preparation", "programme_code": "NEET-2027", "programme_category": "HIGHER_EDUCATION_ENTRANCE", "examination_name": "NEET", "examination_authority": "National Testing Agency", "target_purpose": "Medical entrance preparation", "description": "Structured NEET learning", "is_active": True}, "subject": physics if subject_scope else None, "subjects": subjects, "coordinators": [{"name": "Dr. B Sudhakar", "employee_code": "602867", "department": "COMPUTER SCIENCE", "designation": "Degree Lecturer"}], "experts": [{"name": "Physics Expert", "employee_code": "PHY-01", "department": "PHYSICS", "subject_name": "Physics"}], "activity": {"students": 12, "learning_sessions": 3, "completed_learning_sessions": 1, "assessments": 2, "published_assessments": 1, "assessment_attempts": 8, "average_percentage": 72.5, "questions": 44, "remedial_groups": 1}, "configured": {"subjects": len(subjects), "units": len(subjects), "topics": 1, "subtopics": 2}, "weightage_readiness": "80% configured"}


class CourseProfilePdfTests(unittest.TestCase):
    def test_course_profile_pdf_contains_branding_identity_ownership_and_activity(self):
        content = build_course_profile_pdf(report_payload(), generated_by="SYS Administrator", generated_at=datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc))
        self.assertTrue(content.startswith(b"%PDF-"))
        for expected in [b"SYS - Strengthen Your Skills", b"Shape Your Successful Future", b"NEET Preparation", b"NEET-2027", b"Dr. B Sudhakar", b"Academic ownership", b"Student participation", b"Learning activity", b"Assessment and performance summary", b"Question bank and academic intelligence", b"Remedial learning and academic support", b"Course readiness", b"IST", b"Confidential"]:
            self.assertIn(expected, content, expected)

    def test_subject_profile_excludes_unassigned_subject_data(self):
        content = build_course_profile_pdf(report_payload(subject_scope=True), generated_by="Physics Expert")
        self.assertIn(b"Physics", content)
        self.assertIn(b"Subject readiness", content)
        self.assertNotIn(b"Organic Chemistry", content)

    def test_course_syllabus_pdf_contains_full_weighted_hierarchy(self):
        content = build_course_profile_pdf(report_payload(), generated_by="SYS Coordinator", report_type="syllabus")
        for expected in [b"Physics", b"Chemistry", b"Mechanics", b"Kinematics", b"Motion", b"Velocity", b"60%", b"40%"]:
            self.assertIn(expected, content, expected)

    def test_subject_syllabus_pdf_excludes_other_course_subjects(self):
        content = build_course_profile_pdf(report_payload(subject_scope=True), generated_by="Physics Expert", report_type="syllabus")
        self.assertIn(b"Mechanics", content)
        self.assertNotIn(b"Organic Chemistry", content)

    def test_large_syllabus_repeats_branding_across_multiple_pages(self):
        content = build_course_profile_pdf(report_payload(large=True), generated_by="SYS Coordinator", report_type="syllabus")
        self.assertGreater(content.count(b"SYS - Strengthen Your Skills"), 1)
        self.assertIn(b"Physics topic 54", content)

    def test_coordinator_portfolio_contains_every_assigned_course(self):
        first = report_payload()
        second = report_payload()
        second["course"] = dict(second["course"], id=2, title="TGPCPWT Preparation", programme_code="TGPCPWT-2026")
        content = build_coordinator_courses_pdf([first, second], generated_by="Dr. B Sudhakar")
        self.assertTrue(content.startswith(b"%PDF-"))
        for expected in [b"Assigned Course Portfolio", b"NEET Preparation", b"NEET-2027", b"TGPCPWT Preparation", b"TGPCPWT-2026", b"Dr. B Sudhakar"]:
            self.assertIn(expected, content)

    def test_subject_expert_portfolio_groups_assignments_across_courses(self):
        first = report_payload(subject_scope=True)
        second = report_payload(subject_scope=True)
        second["course"] = dict(second["course"], id=2, title="TGPCPWT Preparation", programme_code="TGPCPWT-2026")
        second["subject"] = dict(second["subject"], id=12, name="Arithmetic")
        second["subjects"] = [second["subject"]]
        content = build_subject_expert_assignments_pdf([first, second], generated_by="Dr. B Sudhakar")
        self.assertTrue(content.startswith(b"%PDF-"))
        for expected in [b"Assigned Subject Portfolio", b"Physics", b"NEET Preparation", b"Arithmetic", b"TGPCPWT Preparation", b"Dr. B Sudhakar"]:
            self.assertIn(expected, content)

    def test_report_routes_enforce_course_and_subject_ownership(self):
        routes = (ROOT / "app" / "routes" / "admin.py").read_text(encoding="utf-8")
        for path in ['"/courses/{course_id}/profile.pdf"', '"/courses/{course_id}/syllabus.pdf"', '"/courses/{course_id}/subjects/{subject_id}/profile.pdf"', '"/courses/{course_id}/subjects/{subject_id}/syllabus.pdf"']:
            self.assertIn(path, routes)
        self.assertIn("Only an assigned course coordinator or administrator can download the complete course report", routes)
        self.assertIn("Subject expert responsibility is required to download this subject report", routes)
        self.assertIn('action=f"{scope_name.lower()}.report.download"', routes)
        self.assertIn('"/course-coordinators/my-courses.pdf"', routes)
        self.assertIn('action="course_coordinator.portfolio.download"', routes)
        self.assertIn('"/subject-experts/my-subjects.pdf"', routes)
        self.assertIn('action="subject_expert.portfolio.download"', routes)

    def test_invalid_report_types_are_rejected(self):
        with self.assertRaises(ValueError):
            build_course_profile_pdf(report_payload(), generated_by="SYS Administrator", report_type="student-list")


if __name__ == "__main__":
    unittest.main()
