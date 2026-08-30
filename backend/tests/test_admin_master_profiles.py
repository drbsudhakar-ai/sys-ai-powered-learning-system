"""Administrator-only institutional student/faculty profiles and PDF exports."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import isolation as _test_isolation  # noqa: E402,F401
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database, models, utils  # noqa: E402
from app.routes import admin, admin_management, auth  # noqa: E402


class AdminMasterProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.sessions = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        for table in (models.User.__table__, models.AdminAuditLog.__table__, models.Course.__table__, models.StudentCourseEnrollment.__table__, models.FacultyCourseAssignment.__table__, models.Subject.__table__, models.SubjectExpertAssignment.__table__):
            table.create(bind=cls.engine)
        application = FastAPI()
        application.include_router(auth.router)
        application.include_router(admin.router)
        application.include_router(admin_management.router)

        def override_db():
            session = cls.sessions()
            try:
                yield session
            finally:
                session.close()

        application.dependency_overrides[database.get_db] = override_db
        cls.client = TestClient(application)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.engine.dispose()

    def _admin_headers(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"profile-admin-{suffix}@example.com"
        password = "TestPass123!"
        with self.sessions() as session:
            session.add(models.User(name="SYS Administrator", email=email, role="admin", hashed_password=utils.hash_password(password), account_status="ACTIVE", is_active=True))
            session.commit()
        response = self.client.post("/auth/login", data={"username": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def _student(self, headers):
        suffix = uuid.uuid4().hex[:8]
        response = self.client.post("/admin/students", headers=headers, json={"name": "SYS Profile Student", "roll_number": f"STU-{suffix}", "email": f"student-{suffix}@example.com", "mobile_number": f"+919{int(suffix, 16) % 1_000_000_000:09d}", "college": "MJPTBCWRDC-Narayanpet", "academic_program": "B.Sc.(MPCS)", "photo_url": "/photos/student.jpg"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _non_admin_headers(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"profile-user-{suffix}@example.com"
        password = "TestPass123!"
        with self.sessions() as session:
            session.add(models.User(name="Non-admin Student", email=email, role="student", roll_number=f"LOGIN-{suffix.upper()}", hashed_password=utils.hash_password(password), account_status="ACTIVE", is_active=True))
            session.commit()
        response = self.client.post("/auth/login", data={"username": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def _faculty(self, headers):
        suffix = uuid.uuid4().hex[:8]
        response = self.client.post("/admin/faculty", headers=headers, json={"name": "SYS Profile Faculty", "employee_code": f"FAC-{suffix}", "email": f"faculty-{suffix}@example.com", "college": "MJPTBCWRDC-Narayanpet", "department": "Computer Science", "designation": "Degree Lecturer", "photo_url": "/photos/faculty.jpg"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_student_profile_contains_photo_contact_and_enrolled_sys_courses(self):
        headers = self._admin_headers()
        student = self._student(headers)
        with self.sessions() as session:
            course = models.Course(title="GATE Preparation")
            session.add(course)
            session.flush()
            session.add(models.StudentCourseEnrollment(student_id=student["id"], course_id=course.id))
            session.commit()
        response = self.client.get(f"/admin/master/students/{student['id']}/profile", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        record = response.json()["record"]
        self.assertEqual(record["photo_url"], "/photos/student.jpg")
        self.assertEqual(record["academic_program"], "B.Sc.(MPCS)")
        self.assertEqual(record["programmes"][0]["title"], "GATE Preparation")
        self.assertEqual(record["mobile_number"], student["institutional_mobile"])

    def test_student_profile_contains_every_activity_section_without_invented_data(self):
        headers = self._admin_headers()
        student = self._student(headers)
        response = self.client.get(f"/admin/master/students/{student['id']}/profile", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        activity = response.json()["activity"]
        for section in ["learning", "assessments", "performance", "remediation", "mastery", "journey", "support", "notifications"]:
            self.assertIn(section, activity)
        self.assertEqual(activity["learning"]["total"], 0)
        self.assertEqual(activity["assessments"]["attempted"], 0)
        self.assertIsNone(activity["assessments"]["average_percentage"])
        self.assertIsNone(activity["journey"]["next_action"])

    def test_faculty_profile_contains_existing_course_and_subject_assignments(self):
        headers = self._admin_headers()
        faculty = self._faculty(headers)
        with self.sessions() as session:
            course = models.Course(title="GATE Preparation")
            subject = models.Subject(name=f"Data Structures {uuid.uuid4().hex[:6]}")
            session.add_all([course, subject])
            session.flush()
            session.add_all([models.FacultyCourseAssignment(faculty_id=faculty["id"], course_id=course.id), models.SubjectExpertAssignment(faculty_id=faculty["id"], subject_id=subject.id)])
            session.commit()
        response = self.client.get(f"/admin/master/faculty/{faculty['id']}/profile", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["record"]["photo_url"], "/photos/faculty.jpg")
        self.assertEqual(response.json()["coordinator_courses"][0]["title"], "GATE Preparation")
        self.assertTrue(response.json()["expert_subjects"][0]["name"].startswith("Data Structures"))

    def test_faculty_profile_contains_every_activity_section_without_invented_data(self):
        headers = self._admin_headers()
        faculty = self._faculty(headers)
        response = self.client.get(f"/admin/master/faculty/{faculty['id']}/profile", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        activity = response.json()["activity"]
        for section in ["teaching", "assessments", "oversight", "remediation", "content", "notifications"]:
            self.assertIn(section, activity)
        self.assertEqual(activity["teaching"]["total"], 0)
        self.assertEqual(activity["assessments"]["created"], 0)
        self.assertEqual(activity["oversight"]["students"], 0)

    def test_student_profile_pdf_is_branded_and_identifiable(self):
        headers = self._admin_headers()
        student = self._student(headers)
        response = self.client.get(f"/admin/master/students/{student['id']}/profile.pdf", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn(student["roll_number"], response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"SYS Profile Student", response.content)

    def test_faculty_profile_pdf_contains_real_responsibility_details(self):
        headers = self._admin_headers()
        faculty = self._faculty(headers)
        response = self.client.get(f"/admin/master/faculty/{faculty['id']}/profile.pdf", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(faculty["employee_code"], response.headers["content-disposition"])
        self.assertIn(b"Degree Lecturer", response.content)

    def test_profiles_and_pdfs_reject_unauthenticated_requests(self):
        for path in ["/admin/master/students/1/profile", "/admin/master/students/1/profile.pdf", "/admin/master/faculty/1/profile", "/admin/master/faculty/1/profile.pdf"]:
            self.assertEqual(self.client.get(path).status_code, 401, path)

    def test_profiles_and_pdfs_reject_authenticated_non_administrators(self):
        headers = self._non_admin_headers()
        for path in ["/admin/master/students/1/profile", "/admin/master/students/1/profile.pdf", "/admin/master/faculty/1/profile", "/admin/master/faculty/1/profile.pdf"]:
            self.assertEqual(self.client.get(path, headers=headers).status_code, 403, path)

    def test_profile_returns_not_found_for_wrong_role(self):
        headers = self._admin_headers()
        student = self._student(headers)
        response = self.client.get(f"/admin/master/faculty/{student['id']}/profile", headers=headers)
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()
