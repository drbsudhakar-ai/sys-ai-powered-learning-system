"""Student academic-programme persistence and master presentation checks."""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from io import BytesIO
from zipfile import ZipFile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import isolation as _test_isolation  # noqa: E402,F401
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database, models, utils  # noqa: E402
from app.routes import admin, admin_management, auth  # noqa: E402


class StudentAcademicProgrammeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        for table in (models.User.__table__, models.AdminAuditLog.__table__, models.Course.__table__, models.StudentCourseEnrollment.__table__):
            table.create(bind=cls.engine)

        application = FastAPI()
        application.include_router(auth.router)
        application.include_router(admin.router)
        application.include_router(admin_management.router)

        def override_db():
            session = cls.session_factory()
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

    def _headers(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"programme-admin-{suffix}@example.com"
        password = "TestPass123!"
        with self.session_factory() as session:
            session.add(models.User(
                name="Programme Administrator",
                email=email,
                role="admin",
                hashed_password=utils.hash_password(password),
                account_status="ACTIVE",
                is_active=True,
            ))
            session.commit()
        response = self.client.post("/auth/login", data={"username": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def _student_payload(self, **overrides):
        suffix = uuid.uuid4().hex[:8]
        return {
            "name": "SYS Programme Student",
            "roll_number": f"STU-{suffix}",
            "email": f"programme-student-{suffix}@example.com",
            "college": "MJPTBCWRDC-Narayanpet",
            "academic_program": "B.Sc.(MPCS)",
            "admission_year": 2024,
            "present_year": 3,
            "academic_status": "ACTIVE",
            **overrides,
        }

    def test_individual_creation_persists_and_returns_academic_programme(self):
        payload = self._student_payload(academic_program="  B.Sc.(MPCS)  ")
        response = self.client.post("/admin/students", headers=self._headers(), json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["academic_program"], "B.Sc.(MPCS)")
        with self.session_factory() as session:
            student = session.query(models.User).filter_by(id=response.json()["id"]).one()
            self.assertEqual(student.academic_program, "B.Sc.(MPCS)")

    def test_master_listing_includes_academic_programme_without_sys_enrolment(self):
        headers = self._headers()
        created = self.client.post("/admin/students", headers=headers, json=self._student_payload())
        self.assertEqual(created.status_code, 201, created.text)
        response = self.client.get("/admin/master/students", headers=headers, params={"search": created.json()["roll_number"]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"][0]["academic_program"], "B.Sc.(MPCS)")
        self.assertEqual(response.json()["items"][0]["programmes"], [])

    def test_student_academic_programme_can_be_updated(self):
        headers = self._headers()
        created = self.client.post("/admin/students", headers=headers, json=self._student_payload())
        response = self.client.put(
            f"/admin/students/{created.json()['id']}",
            headers=headers,
            json={"academic_program": " B.Com.(CA) "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["academic_program"], "B.Com.(CA)")

    def test_student_export_uses_institutional_academic_programme(self):
        headers = self._headers()
        created = self.client.post("/admin/students", headers=headers, json=self._student_payload())
        response = self.client.get(
            "/admin/master/students/export",
            headers=headers,
            params={"search": created.json()["roll_number"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(".xlsx", response.headers["content-disposition"])
        with ZipFile(BytesIO(response.content)) as workbook:
            worksheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("B.Sc.(MPCS)", worksheet)

    def test_faculty_cannot_receive_student_academic_programme(self):
        suffix = uuid.uuid4().hex[:8]
        response = self.client.post(
            "/admin/faculty",
            headers=self._headers(),
            json={
                "name": "SYS Lecturer",
                "employee_code": f"FAC-{suffix}",
                "email": f"faculty-{suffix}@example.com",
                "academic_program": "B.Sc.(MPCS)",
            },
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
