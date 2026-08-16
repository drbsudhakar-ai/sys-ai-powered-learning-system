"""P0-020.1 normalized institutional identifier regression coverage."""

from __future__ import annotations

import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from tests.auth_helpers import ProtectedUserFactory
from app import database, models
from app.main import app


client = TestClient(app)
_users = ProtectedUserFactory(client, "P0201")


def _identifier(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}".upper()


class InstitutionalIdentifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _users.create("admin")
        cls.headers = {"Authorization": f"Bearer {cls.admin.token}"}

    def _student(self, roll_number: str | None, *, include: bool = True):
        payload = {"name": "Identifier Student"}
        if include:
            payload["roll_number"] = roll_number
        return client.post("/admin/students", headers=self.headers, json=payload)

    def _faculty(self, employee_code: str | None, *, include: bool = True):
        payload = {"name": "Identifier Faculty"}
        if include:
            payload["employee_code"] = employee_code
        return client.post("/admin/faculty", headers=self.headers, json=payload)

    def test_exact_duplicate_roll_number(self):
        identifier = _identifier("EXACT")
        self.assertEqual(self._student(identifier).status_code, 201)
        duplicate = self._student(identifier)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["detail"], "Roll number already exists")

    def test_case_only_duplicate_employee_code(self):
        identifier = _identifier("CASE")
        self.assertEqual(self._faculty(identifier).status_code, 201)
        duplicate = self._faculty(identifier.lower())
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["detail"], "Employee code already exists")

    def test_space_only_difference_is_duplicate(self):
        identifier = _identifier("SPACE")
        self.assertEqual(self._student(identifier).status_code, 201)
        duplicate = self._student(f"  {identifier.lower()}  ")
        self.assertEqual(duplicate.status_code, 409)

    def test_blank_identifiers_are_rejected(self):
        student = self._student("   ")
        faculty = self._faculty("\t")
        self.assertEqual(student.status_code, 422)
        self.assertEqual(student.json()["detail"], "roll_number is required for students")
        self.assertEqual(faculty.status_code, 422)
        self.assertEqual(faculty.json()["detail"], "employee_code is required for faculty")

    def test_role_identifier_is_required(self):
        self.assertEqual(self._student(None, include=False).status_code, 422)
        self.assertEqual(self._faculty(None, include=False).status_code, 422)

    def test_valid_distinct_identifiers_are_normalized(self):
        roll_number = _identifier("ROLL")
        employee_code = _identifier("EMP")
        student = self._student(f"  {roll_number.lower()}  ")
        faculty = self._faculty(f"  {employee_code.lower()}  ")
        self.assertEqual(student.status_code, 201, student.text)
        self.assertEqual(faculty.status_code, 201, faculty.text)
        self.assertEqual(student.json()["roll_number"], roll_number)
        self.assertEqual(faculty.json()["employee_code"], employee_code)

    def test_concurrent_duplicate_creation_allows_only_one(self):
        identifier = _identifier("RACE")

        def create(suffix: int) -> int:
            return client.post(
                "/admin/students",
                headers=self.headers,
                json={"name": f"Concurrent Student {suffix}", "roll_number": identifier},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = sorted(executor.map(create, range(2)))
        self.assertEqual(statuses, [201, 409])

    def test_duplicate_rows_inside_master_upload_are_atomic(self):
        identifier = _identifier("BATCH")
        response = client.post(
            "/admin/users/master-upload",
            headers=self.headers,
            json={
                "records": [
                    {"role": "student", "name": "Batch One", "roll_number": identifier},
                    {
                        "role": "student",
                        "name": "Batch Two",
                        "roll_number": f" {identifier.lower()} ",
                    },
                ]
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Duplicate roll number in master-upload batch",
        )
        with database.SessionLocal() as db:
            count = (
                db.query(models.User)
                .filter(models.User.roll_number == identifier)
                .count()
            )
        self.assertEqual(count, 0)

    def test_master_upload_rejects_existing_database_identifier(self):
        identifier = _identifier("EXISTING")
        self.assertEqual(self._faculty(identifier).status_code, 201)
        response = client.post(
            "/admin/users/master-upload",
            headers=self.headers,
            json={
                "records": [
                    {
                        "role": "faculty",
                        "name": "Existing Faculty",
                        "employee_code": f" {identifier.lower()} ",
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Employee code already exists")

    def test_database_rejects_direct_duplicate_and_missing_role_identifier(self):
        identifier = _identifier("DIRECT")
        with database.SessionLocal() as db:
            db.add(
                models.User(
                    name="Direct One",
                    role="student",
                    roll_number=identifier,
                    account_status="PENDING_ACTIVATION",
                )
            )
            db.commit()
            db.add(
                models.User(
                    name="Direct Duplicate",
                    role="student",
                    roll_number=identifier,
                    account_status="PENDING_ACTIVATION",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            db.add(
                models.User(
                    name="Missing Roll",
                    role="student",
                    account_status="PENDING_ACTIVATION",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_admin_remains_valid_without_institutional_identifier(self):
        with database.SessionLocal() as db:
            admin = models.User(
                name="Identifier Contract Admin",
                role="admin",
                account_status="PENDING_ACTIVATION",
            )
            db.add(admin)
            db.commit()
            self.assertIsNotNone(admin.id)


if __name__ == "__main__":
    unittest.main()
