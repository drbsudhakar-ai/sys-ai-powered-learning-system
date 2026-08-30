"""Regression coverage for branded student and faculty profile documents."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from app.services.master_profile_pdf import _default_profile_photo_url, _local_photo, build_master_profile_pdf


class MasterProfilePdfTests(unittest.TestCase):
    def _student(self):
        return {
            "record": {
                "id": 5, "role": "student", "name": "AVUTI VIKAS", "roll_number": "240334524681001",
                "photo_url": None, "email": "student@example.com", "mobile_number": "+918639228255",
                "email_verified": True, "mobile_verified": False, "registration_status": "ACTIVE", "is_active": True,
                "college": "MJPTBCWRDC-NARAYANPET", "academic_program": "B.Sc.(MPCS)", "admission_year": 2024,
                "present_year": 3, "academic_status": "ACTIVE", "programmes": [{"id": 1, "title": "GATE Preparation"}],
                "created_at": datetime(2026, 8, 23, 11, 30, tzinfo=timezone.utc), "updated_at": None,
                "last_login_available": False,
            },
            "coordinator_courses": [], "expert_subjects": [],
        }

    def _faculty(self):
        profile = self._student()
        profile["record"].update({
            "role": "faculty", "name": "Dr. B Sudhakar", "roll_number": None, "employee_code": "602867",
            "department": "COMPUTER SCIENCE", "designation": "Degree Lecturer", "employment_status": "ACTIVE",
            "registration_status": "PENDING_ACTIVATION", "programmes": [],
        })
        profile["coordinator_courses"] = [{"id": 1, "title": "GATE Preparation"}]
        profile["expert_subjects"] = [{"id": 3, "name": "Data Structures"}]
        return profile

    def test_student_document_contains_brand_identity_contacts_and_courses(self):
        content = build_master_profile_pdf(self._student(), generated_by="SYS Administrator")
        self.assertTrue(content.startswith(b"%PDF-"))
        for expected in [b"Strengthen Your Skills", b"Shape Your Successful Future", b"AVUTI VIKAS", b"240334524681001", b"+918639228255", b"GATE Preparation", b"Registered SYS courses"]:
            self.assertIn(expected, content)

    def test_faculty_document_contains_real_academic_responsibilities(self):
        content = build_master_profile_pdf(self._faculty(), generated_by="SYS Administrator")
        for expected in [b"Dr. B Sudhakar", b"602867", b"Degree Lecturer", b"Academic responsibilities", b"GATE Preparation", b"Data Structures", b"Pending registration"]:
            self.assertIn(expected, content)

    def test_student_document_includes_every_learning_module_with_truthful_empty_states(self):
        content = build_master_profile_pdf(self._student(), generated_by="SYS Administrator")
        for expected in [
            b"Learning sessions and progress", b"Learning has not started yet", b"Assessment performance",
            b"No assessments attempted yet", b"Performance analysis and learning gaps", b"Remedial learning and interventions",
            b"Topic mastery and adaptive practice", b"Learning journey and next action", b"Early warnings and student support",
            b"English communication and skill development", b"Notifications and engagement",
        ]:
            self.assertIn(expected, content)

    def test_faculty_document_includes_teaching_assessment_oversight_and_support(self):
        content = build_master_profile_pdf(self._faculty(), generated_by="SYS Administrator")
        for expected in [
            b"Teaching and learning sessions", b"No teaching sessions have started yet", b"Assessment creation and evaluation",
            b"Student performance and academic oversight", b"Remedial guidance and interventions",
            b"Question bank and academic content", b"Notifications and engagement",
        ]:
            self.assertIn(expected, content)

    def test_document_includes_ist_administrator_and_confidentiality(self):
        issued_at = datetime(2026, 8, 23, 12, 15, tzinfo=timezone.utc)
        content = build_master_profile_pdf(self._student(), generated_by="SYS Administrator", generated_at=issued_at)
        for expected in [b"23 Aug 2026", b"05:45:00 PM", b"IST", b"SYS Administrator", b"Confidential", b"authorized institutional use only"]:
            self.assertIn(expected, content)

    def test_no_photo_uses_initials_without_failing(self):
        content = build_master_profile_pdf(self._student(), generated_by="Administrator")
        self.assertIn(b"AV", content)

    def test_photo_loader_rejects_external_and_parent_traversal_locations(self):
        self.assertIsNone(_local_photo("https://example.com/photo.png"))
        self.assertIsNone(_local_photo("http://127.0.0.1/private.png"))
        self.assertIsNone(_local_photo("/../../backend/.env"))

    def test_default_profile_photo_matches_safe_institutional_identifier(self):
        self.assertEqual(_default_profile_photo_url({"employee_code": "602867"}, "faculty"), "/photos/faculty-602867.jpg")
        self.assertEqual(_default_profile_photo_url({"roll_number": "240334524681001"}, "student"), "/photos/student-240334524681001.jpg")
        self.assertIsNone(_default_profile_photo_url({"employee_code": "../../private"}, "faculty"))
        self.assertIsNone(_default_profile_photo_url({"employee_code": "602867"}, "administrator"))


if __name__ == "__main__":
    unittest.main()
