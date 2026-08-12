"""
Course Management API tests (P0-007).
Uses FastAPI TestClient against the real app + configured DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

# Ensure backend package root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_and_login(role: str, extra: dict) -> str:
    email = _unique_email(role)
    payload = {
        "name": f"P007 {role}",
        "email": email,
        "role": role,
        "password": "TestPass123!",
        **extra,
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/auth/login",
        data={"username": email, "password": "TestPass123!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class CourseManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.student = _register_and_login("student", {"roll_number": "P007S"})
        cls.faculty = _register_and_login("faculty", {"employee_code": "P007F"})
        cls.admin = _register_and_login("admin", {"employee_code": "P007A"})

    def test_unauthenticated_list_rejected(self):
        res = client.get("/courses/")
        self.assertEqual(res.status_code, 401)

    def test_student_can_list_but_not_create(self):
        listed = client.get("/courses/", headers=_auth(self.student))
        self.assertEqual(listed.status_code, 200)
        created = client.post(
            "/courses/",
            headers=_auth(self.student),
            json={"title": "Nope", "description": "denied"},
        )
        self.assertEqual(created.status_code, 403)

    def test_faculty_create_get_update_delete(self):
        created = client.post(
            "/courses/",
            headers=_auth(self.faculty),
            json={
                "title": "P007 Faculty Course",
                "description": "Initial",
                "syllabus_url": "https://example.com/syllabus",
                "resources_url": None,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        self.assertEqual(body["title"], "P007 Faculty Course")
        self.assertIn("created_at", body)
        course_id = body["id"]

        detail = client.get(f"/courses/{course_id}", headers=_auth(self.student))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], course_id)

        updated = client.put(
            f"/courses/{course_id}",
            headers=_auth(self.faculty),
            json={"title": "P007 Updated", "description": "Changed"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "P007 Updated")

        deleted = client.delete(
            f"/courses/{course_id}",
            headers=_auth(self.faculty),
        )
        self.assertEqual(deleted.status_code, 204)

        missing = client.get(f"/courses/{course_id}", headers=_auth(self.faculty))
        self.assertEqual(missing.status_code, 404)

    def test_admin_can_create(self):
        res = client.post(
            "/courses/",
            headers=_auth(self.admin),
            json={"title": "P007 Admin Course", "description": "Admin"},
        )
        self.assertEqual(res.status_code, 201)

    def test_validation_rejects_empty_title(self):
        res = client.post(
            "/courses/",
            headers=_auth(self.faculty),
            json={"title": "", "description": "bad"},
        )
        self.assertEqual(res.status_code, 422)

    def test_not_found_and_student_cannot_delete(self):
        created = client.post(
            "/courses/",
            headers=_auth(self.faculty),
            json={"title": "P007 Temp", "description": "temp"},
        )
        course_id = created.json()["id"]
        denied = client.delete(
            f"/courses/{course_id}",
            headers=_auth(self.student),
        )
        self.assertEqual(denied.status_code, 403)
        missing = client.get("/courses/99999999", headers=_auth(self.faculty))
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
