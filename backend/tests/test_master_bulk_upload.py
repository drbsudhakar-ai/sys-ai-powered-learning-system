"""Security and persistence coverage for student and faculty master imports."""

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
from app.routes import auth, faculty, students  # noqa: E402


class MasterBulkUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        models.User.__table__.create(bind=cls.engine)
        models.AdminAuditLog.__table__.create(bind=cls.engine)

        test_app = FastAPI()
        test_app.include_router(auth.router)
        test_app.include_router(students.router)
        test_app.include_router(faculty.router)

        def override_db():
            session = cls.session_factory()
            try:
                yield session
            finally:
                session.close()

        test_app.dependency_overrides[database.get_db] = override_db
        cls.client = TestClient(test_app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.engine.dispose()

    def _headers(self, role="admin"):
        suffix = uuid.uuid4().hex[:8]
        password = "TestPass123!"
        email = f"{role}-{suffix}@example.com"
        user = models.User(
            name=f"Upload {role}",
            email=email,
            role=role,
            roll_number=f"STU-{suffix}".upper() if role == "student" else None,
            employee_code=f"EMP-{suffix}".upper() if role == "faculty" else None,
            hashed_password=utils.hash_password(password),
            account_status="ACTIVE",
            is_active=True,
        )
        with self.session_factory() as session:
            session.add(user)
            session.commit()

        response = self.client.post("/auth/login", data={"username": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def _faculty(self, identifier=None):
        suffix = uuid.uuid4().hex[:8]
        return {
            "employee_code": identifier or f"FAC-{suffix}",
            "name": "SYS Faculty Member",
            "email": f"faculty-{suffix}@example.com",
            "mobile_number": f"9{int(suffix, 16) % 1_000_000_000:09d}",
            "college": "SYS Welfare Degree College",
            "department": "Computer Science",
            "designation": "Lecturer",
            "employment_status": "active",
        }

    def _student(self):
        record = self._faculty()
        record.update(
            roll_number=f"STU-{uuid.uuid4().hex[:8]}",
            academic_program="B.Sc Computer Science",
            admission_year=2025,
            present_year=2,
            academic_status="active",
        )
        record.pop("employee_code")
        record.pop("designation")
        record.pop("employment_status")
        return record

    def test_upload_requires_authenticated_administrator(self):
        for path, payload in (("/faculty/bulk", [self._faculty()]), ("/students/bulk", [self._student()])):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, json=payload).status_code, 401)
                self.assertEqual(self.client.post(path, headers=self._headers("student"), json=payload).status_code, 403)

    def test_faculty_upload_creates_pending_master_and_audit(self):
        record = self._faculty()
        response = self.client.post("/faculty/bulk", headers=self._headers(), json=[record])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["inserted"], 1)

        with self.session_factory() as session:
            user = session.query(models.User).filter(models.User.employee_code == record["employee_code"].upper()).one()
            self.assertEqual(user.role, "faculty")
            self.assertEqual(user.account_status, "PENDING_ACTIVATION")
            self.assertEqual(user.institutional_email, record["email"])
            self.assertEqual(user.institutional_mobile, f"+91{record['mobile_number']}")
            self.assertEqual(user.employment_status, "ACTIVE")
            self.assertIsNone(user.email)
            self.assertIsNone(user.hashed_password)
            self.assertIsNotNone(session.query(models.AdminAuditLog).filter_by(action="master.faculty.bulk_upload").first())

    def test_duplicate_employee_codes_are_skipped(self):
        record = self._faculty()
        response = self.client.post("/faculty/bulk", headers=self._headers(), json=[record, dict(record)])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["inserted"], 1)
        self.assertEqual(response.json()["skipped"], 1)

    def test_invalid_faculty_rows_are_reported(self):
        record = self._faculty()
        record["employment_status"] = "RETIRED"
        response = self.client.post("/faculty/bulk", headers=self._headers(), json=[record])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["inserted"], 0)
        self.assertEqual(response.json()["invalid"], 1)
        self.assertIn("Employment status", response.json()["invalid_records"][0]["reason"])

    def test_student_upload_preserves_registration_lifecycle(self):
        record = self._student()
        response = self.client.post("/students/bulk", headers=self._headers(), json=[record])
        self.assertEqual(response.status_code, 200, response.text)
        with self.session_factory() as session:
            user = session.query(models.User).filter(models.User.roll_number == record["roll_number"].upper()).one()
            self.assertEqual(user.account_status, "PENDING_ACTIVATION")
            self.assertEqual(user.academic_program, "B.Sc Computer Science")

    def test_empty_upload_is_rejected(self):
        response = self.client.post("/faculty/bulk", headers=self._headers(), json=[])
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
