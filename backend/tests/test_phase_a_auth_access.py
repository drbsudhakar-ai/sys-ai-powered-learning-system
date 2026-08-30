"""Source-level checks for the Phase A identity and dashboard contract."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PhaseAAuthAccessTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_activation_and_recovery_routes_are_exposed(self):
        source = self.read("backend/app/routes/auth.py")
        for route in (
            "/activation/start",
            "/activation/verify-otp",
            "/activation/verify-contact",
            "/activation/complete",
            "/password-reset/start",
            "/password-reset/verify-otp",
            "/password-reset/complete",
        ):
            self.assertIn(route, source)

    def test_dashboard_data_is_scoped_to_authenticated_identity(self):
        source = self.read("backend/app/routes/auth.py")
        self.assertIn("StudentCourseEnrollment.student_id == current_user.id", source)
        self.assertIn("FacultyCourseAssignment.faculty_id == current_user.id", source)
        self.assertIn("SubjectExpertAssignment.faculty_id == current_user.id", source)

    def test_pilot_activation_keeps_mobile_unverified_without_sms(self):
        service = self.read("backend/app/services/authentication.py")
        registration = self.read("frontend/pages/register.js")
        self.assertIn("mobile_verified=bool(mobile_challenge)", service)
        self.assertIn('const ownershipChannel = "email"', registration)
        self.assertIn("mobile_authorization: null", registration)

    def test_legacy_dashboard_is_only_an_authorized_router(self):
        source = self.read("frontend/pages/dashboard.js")
        self.assertIn("getMe()", source)
        self.assertIn("roleLandingPath(data?.role)", source)
        self.assertNotIn("getCourses", source)

    def test_registration_returns_only_masked_institutional_identity(self):
        service = self.read("backend/app/services/authentication.py")
        route = self.read("backend/app/routes/auth.py")
        registration = self.read("frontend/pages/register.js")
        self.assertIn("mask_institutional_email", service)
        self.assertIn("activation_identity_summary", route)
        self.assertIn("Verification code sent to:", registration)
        self.assertIn("the complete email address is not displayed", registration)


if __name__ == "__main__":
    unittest.main()
