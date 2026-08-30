"""Pending assignments and publication activation against an isolated test DB."""
import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import database, models
from app.main import app
from app.services import course_enrollments as service, attempt_engine, course_learning, learning_sessions
from tests.auth_helpers import ProtectedUserFactory

client = TestClient(app)
users = ProtectedUserFactory(client, "PENDING")


class PendingEnrollmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = users.create("admin")
        cls.student = users.create("student", {"roll_number": "PEND-" + uuid.uuid4().hex[:10]})
        cls.faculty = users.create("faculty", {"employee_code": "PEND-" + uuid.uuid4().hex[:10]})

    def setUp(self):
        self.db = database.SessionLocal()
        self.addCleanup(self.db.close)
        self.course = models.Course(title="Pending lifecycle", programme_code=uuid.uuid4().hex[:12],
                                    publication_status="DRAFT", is_active=False, created_by=self.admin.user_id)
        self.db.add(self.course)
        self.db.commit()
        self.url = f"/admin/courses/{self.course.id}"
        self.headers = {"Authorization": f"Bearer {self.admin.token}"}

    def request_bulk(self, **extra):
        return client.post(self.url + "/enrollments/bulk", headers=self.headers,
                           json={"student_ids": [self.student.user_id], **extra})

    def status(self, value="PUBLISHED", active=True):
        self.course.publication_status, self.course.is_active = value, active
        self.db.commit()

    def enrollment(self, state="PENDING_ACTIVATION", student_id=None):
        row = models.StudentCourseEnrollment(course_id=self.course.id, student_id=student_id or self.student.user_id, status=state)
        self.db.add(row); self.db.commit()
        return row

    def publish(self, count, activate=True):
        # Academic readiness has its own regression suite; isolate activation here.
        with patch("app.routes.admin._publication_readiness", return_value={"ready": True}):
            return client.post(self.url + "/publish", headers=self.headers,
                               json={"activate_pending": activate, "expected_pending_count": count})

    def test_draft_preview_is_read_only_and_assignment_is_pending(self):
        response = client.post(self.url + "/enrollments/preview", headers=self.headers,
                               json={"student_ids": [self.student.user_id]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["summary"]["ready"], 1)
        self.assertEqual(self.db.query(models.StudentCourseEnrollment).filter_by(course_id=self.course.id).count(), 0)
        response = self.request_bulk()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "PENDING_ACTIVATION")
        self.assertEqual(self.request_bulk().json()["skipped"], 1)
        audit = self.db.query(models.AdminAuditLog).filter_by(target_id=self.course.id, action="course.enrollment.bulk").first()
        self.assertEqual(audit.details["status"], "PENDING_ACTIVATION")

    def test_review_pending_and_published_active(self):
        self.status("READY_FOR_REVIEW", False)
        self.assertEqual(self.request_bulk().json()["status"], "PENDING_ACTIVATION")
        self.status()
        response = client.patch(self.url + "/enrollments/" + str(self.db.query(models.StudentCourseEnrollment).filter_by(course_id=self.course.id).first().id), headers=self.headers, json={"status": "ACTIVE"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(service.has_learning_access(self.db, self.student.user_id, self.course.id))

    def test_unavailable_courses_and_non_admins_cannot_assign(self):
        for state in ("ARCHIVED", "PUBLISHED"):
            self.status(state, False)
            self.assertEqual(self.request_bulk().status_code, 409)
        for identity in (self.student, self.faculty):
            response = client.post(self.url + "/enrollments/bulk", headers={"Authorization": f"Bearer {identity.token}"}, json={"student_ids": [self.student.user_id]})
            self.assertEqual(response.status_code, 403)

    def test_pending_cannot_be_activated_or_completed_in_draft(self):
        row = self.enrollment()
        for status in ("ACTIVE", "COMPLETED"):
            response = client.patch(self.url + f"/enrollments/{row.id}", headers=self.headers, json={"status": status})
            self.assertEqual(response.status_code, 409, response.text)

    def test_publication_confirmation_activates_and_audits(self):
        self.enrollment()
        readiness = client.get(self.url + "/publication-readiness", headers=self.headers)
        self.assertEqual(readiness.json()["pending_enrollment_count"], 1)
        response = self.publish(1)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["enrollment_activation"]["activated"], 1)
        self.db.expire_all()
        self.assertTrue(service.has_learning_access(self.db, self.student.user_id, self.course.id))
        self.assertIsNotNone(self.db.query(models.AdminAuditLog).filter_by(action="course.enrollment.activate_pending", target_id=self.course.id).first())
        self.assertEqual(self.publish(0).json()["enrollment_activation"]["activated"], 0)

    def test_stale_count_fails_without_publishing(self):
        self.enrollment()
        self.assertEqual(self.publish(0).status_code, 409)
        self.db.refresh(self.course)
        self.assertEqual(self.course.publication_status, "DRAFT")

    def test_publication_without_consent_leaves_pending(self):
        row = self.enrollment()
        self.assertEqual(self.publish(1, activate=False).status_code, 200)
        self.db.refresh(row)
        self.assertEqual(row.status, "PENDING_ACTIVATION")
        self.assertFalse(service.has_learning_access(self.db, self.student.user_id, self.course.id))

    def test_ineligible_skipped_and_other_lifecycle_states_preserved(self):
        rows = []
        for state in ("PENDING_ACTIVATION", "WITHDRAWN", "SUSPENDED", "COMPLETED"):
            student = models.User(name="Fixture", role="student", roll_number="PEND-" + uuid.uuid4().hex[:12].upper(), is_active=state != "PENDING_ACTIVATION", academic_status="ACTIVE")
            self.db.add(student); self.db.commit()
            rows.append(self.enrollment(state, student.id))
        response = self.publish(1)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["enrollment_activation"]["skipped"], 1)
        self.db.expire_all()
        self.assertEqual([r.status for r in rows], ["PENDING_ACTIVATION", "WITHDRAWN", "SUSPENDED", "COMPLETED"])

    def test_pending_denied_learning_assessment_and_existing_session(self):
        self.status()
        self.enrollment()
        student = self.db.get(models.User, self.student.user_id)
        self.assertFalse(attempt_engine.is_student_enrolled(self.db, student.id, self.course.id))
        with self.assertRaises(HTTPException):
            course_learning._published_enrollment(self.db, student, self.course.id)
        session = models.LearningSession(id=-100, course_id=self.course.id, created_by=student.id, facilitator_id=self.admin.user_id)
        self.assertFalse(learning_sessions.can_view_session(self.db, student, session))
        response = client.get(f"/student/assessments?course_id={self.course.id}", headers={"Authorization": f"Bearer {self.student.token}"})
        self.assertEqual(response.status_code, 403)

    def test_actual_readiness_still_blocks_publication(self):
        self.enrollment()
        response = client.post(self.url + "/publish", headers=self.headers, json={"activate_pending": True, "expected_pending_count": 1})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
