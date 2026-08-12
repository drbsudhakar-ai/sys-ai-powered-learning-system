"""
Admin student/faculty/academic responsibility tests (P0-008).
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> str:
    email = _email(role)
    payload = {
        "name": f"P008 {role}",
        "email": email,
        "role": role,
        "password": "TestPass123!",
        **extra,
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": "TestPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class AdminAcademicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = _register_login("admin", {"employee_code": "P008A"})
        cls.faculty = _register_login("faculty", {"employee_code": "P008F"})
        cls.student = _register_login("student", {"roll_number": "P008S"})

    def test_unauthenticated_and_non_admin_rejected(self):
        self.assertEqual(client.get("/admin/students").status_code, 401)
        self.assertEqual(
            client.get("/admin/students", headers=_auth(self.student)).status_code, 403
        )
        self.assertEqual(
            client.get("/admin/faculty", headers=_auth(self.faculty)).status_code, 403
        )

    def test_student_crud_and_deactivate(self):
        created = client.post(
            "/admin/students",
            headers=_auth(self.admin),
            json={
                "name": "Stu One",
                "email": _email("stu"),
                "password": "TestPass123!",
                "roll_number": "R100",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        sid = created.json()["id"]
        listed = client.get("/admin/students", headers=_auth(self.admin))
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(s["id"] == sid for s in listed.json()))
        updated = client.put(
            f"/admin/students/{sid}",
            headers=_auth(self.admin),
            json={"name": "Stu Updated"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Stu Updated")
        deact = client.post(f"/admin/students/{sid}/deactivate", headers=_auth(self.admin))
        self.assertEqual(deact.status_code, 200)
        self.assertFalse(deact.json()["is_active"])

    def test_faculty_and_responsibilities(self):
        fac = client.post(
            "/admin/faculty",
            headers=_auth(self.admin),
            json={
                "name": "Fac One",
                "email": _email("fac"),
                "password": "TestPass123!",
                "employee_code": "E100",
            },
        )
        self.assertEqual(fac.status_code, 201, fac.text)
        fid = fac.json()["id"]

        course = client.post(
            "/courses/",
            headers=_auth(self.faculty),
            json={"title": "P008 Course", "description": "c"},
        )
        self.assertEqual(course.status_code, 201, course.text)
        cid = course.json()["id"]

        sub = client.post(
            "/admin/subjects",
            headers=_auth(self.admin),
            json={"name": f"Math-{uuid.uuid4().hex[:6]}"},
        )
        self.assertEqual(sub.status_code, 201, sub.text)
        subject_id = sub.json()["id"]

        # student/faculty cannot assign
        self.assertEqual(
            client.post(
                "/admin/course-coordinators",
                headers=_auth(self.student),
                json={"faculty_id": fid, "course_id": cid},
            ).status_code,
            403,
        )
        self.assertEqual(
            client.post(
                "/admin/subject-experts",
                headers=_auth(self.faculty),
                json={"faculty_id": fid, "subject_id": subject_id},
            ).status_code,
            403,
        )

        coord = client.post(
            "/admin/course-coordinators",
            headers=_auth(self.admin),
            json={"faculty_id": fid, "course_id": cid},
        )
        self.assertEqual(coord.status_code, 201, coord.text)
        dup = client.post(
            "/admin/course-coordinators",
            headers=_auth(self.admin),
            json={"faculty_id": fid, "course_id": cid},
        )
        self.assertEqual(dup.status_code, 409)

        expert = client.post(
            "/admin/subject-experts",
            headers=_auth(self.admin),
            json={"faculty_id": fid, "subject_id": subject_id},
        )
        self.assertEqual(expert.status_code, 201, expert.text)

        details = client.get(f"/admin/faculty/{fid}", headers=_auth(self.admin))
        self.assertEqual(details.status_code, 200)
        body = details.json()
        self.assertEqual(len(body["course_coordinator_assignments"]), 1)
        self.assertEqual(len(body["subject_expert_assignments"]), 1)

        course_detail = client.get(f"/courses/{cid}", headers=_auth(self.admin))
        self.assertEqual(course_detail.status_code, 200)
        self.assertTrue(len(course_detail.json().get("course_coordinators", [])) >= 1)

        self.assertEqual(
            client.delete(
                f"/admin/course-coordinators/{coord.json()['id']}",
                headers=_auth(self.admin),
            ).status_code,
            204,
        )
        self.assertEqual(
            client.delete(
                f"/admin/subject-experts/{expert.json()['id']}",
                headers=_auth(self.admin),
            ).status_code,
            204,
        )


if __name__ == "__main__":
    unittest.main()
