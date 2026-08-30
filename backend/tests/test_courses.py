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
from tests.auth_helpers import ProtectedUserFactory  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)
_users = ProtectedUserFactory(client, "P007")


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_and_login(role: str, extra: dict) -> str:
    return _users.create(role, extra).token


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

        detail = client.get(f"/courses/{course_id}", headers=_auth(self.faculty))
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

    def test_course_master_exposes_verified_readiness_counts(self):
        suffix = uuid.uuid4().hex[:8].upper()
        response = client.post(
            "/courses/",
            headers=_auth(self.admin),
            json={"title": f"P023 Course {suffix}", "programme_code": f"P023-{suffix}", "programme_category": "HIGHER_EDUCATION_ENTRANCE", "examination_name": "NEET", "is_active": False},
        )
        self.assertEqual(response.status_code, 201, response.text)
        course = response.json()
        self.assertFalse(course["is_active"])
        for field in ["subject_count", "unit_count", "topic_count", "subtopic_count", "student_count", "subject_expert_count", "assessment_count", "learning_session_count", "question_count"]:
            self.assertEqual(course[field], 0, field)

    def test_course_master_rejects_duplicate_course_codes(self):
        code = f"P023-{uuid.uuid4().hex[:8].upper()}"
        first = client.post("/courses/", headers=_auth(self.admin), json={"title": "P023 Original", "programme_code": code})
        duplicate = client.post("/courses/", headers=_auth(self.admin), json={"title": "P023 Duplicate", "programme_code": code.lower()})
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_course_master_rejects_duplicate_codes_during_edit(self):
        suffix = uuid.uuid4().hex[:8].upper()
        first = client.post("/courses/", headers=_auth(self.admin), json={"title": "P023 First", "programme_code": f"P023-A-{suffix}"})
        second = client.post("/courses/", headers=_auth(self.admin), json={"title": "P023 Second", "programme_code": f"P023-B-{suffix}"})
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        conflict = client.put(f"/courses/{second.json()['id']}", headers=_auth(self.admin), json={"programme_code": first.json()["programme_code"]})
        self.assertEqual(conflict.status_code, 409, conflict.text)

    def test_admin_can_import_complete_syllabus_hierarchy(self):
        suffix = uuid.uuid4().hex[:8].upper()
        course = client.post("/courses/", headers=_auth(self.admin), json={"title": f"Syllabus {suffix}", "programme_code": f"SYL-{suffix}"}).json()
        rows = [
            {"subject": f"Physics {suffix}", "unit": "Mechanics", "topic": "Motion", "subtopic": "Velocity", "unit_sequence": 1},
            {"subject": f"Physics {suffix}", "unit": "Mechanics", "topic": "Motion", "subtopic": "Acceleration", "unit_sequence": 1},
        ]
        imported = client.post(f"/admin/courses/{course['id']}/syllabus/import", headers=_auth(self.admin), json={"rows": rows})
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertEqual(imported.json()["created"], {"subjects": 1, "units": 1, "topics": 1, "subtopics": 2})
        tree = client.get(f"/admin/courses/{course['id']}/syllabus", headers=_auth(self.admin))
        self.assertEqual(tree.status_code, 200, tree.text)
        self.assertEqual(tree.json()["subjects"][0]["units"][0]["topics"][0]["name"], "Motion")
        detail = client.get(f"/courses/{course['id']}", headers=_auth(self.admin))
        self.assertEqual(detail.json()["unit_count"], 1)

    def test_syllabus_import_is_idempotent_and_rejects_student_access(self):
        suffix = uuid.uuid4().hex[:8].upper()
        course = client.post("/courses/", headers=_auth(self.admin), json={"title": f"Repeat {suffix}", "programme_code": f"REP-{suffix}"}).json()
        payload = {"rows": [{"subject": f"Chemistry {suffix}", "unit": "Atoms", "topic": "Atomic Structure", "subtopic": "Electrons"}]}
        denied = client.post(f"/admin/courses/{course['id']}/syllabus/import", headers=_auth(self.student), json=payload)
        self.assertEqual(denied.status_code, 403, denied.text)
        first = client.post(f"/admin/courses/{course['id']}/syllabus/import", headers=_auth(self.admin), json=payload)
        second = client.post(f"/admin/courses/{course['id']}/syllabus/import", headers=_auth(self.admin), json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["created"], {"subjects": 0, "units": 0, "topics": 0, "subtopics": 0})

    def test_same_subject_name_is_allowed_in_different_courses(self):
        suffix = uuid.uuid4().hex[:8].upper()
        first = client.post("/courses/", headers=_auth(self.admin), json={"title": f"NEET {suffix}", "programme_code": f"N-{suffix}"}).json()
        second = client.post("/courses/", headers=_auth(self.admin), json={"title": f"JEE {suffix}", "programme_code": f"J-{suffix}"}).json()
        name = f"Shared Physics {suffix}"
        one = client.post("/admin/subjects", headers=_auth(self.admin), json={"name": name, "course_id": first["id"]})
        two = client.post("/admin/subjects", headers=_auth(self.admin), json={"name": name, "course_id": second["id"]})
        duplicate = client.post("/admin/subjects", headers=_auth(self.admin), json={"name": name, "course_id": first["id"]})
        self.assertEqual(one.status_code, 201, one.text)
        self.assertEqual(two.status_code, 201, two.text)
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_syllabus_items_can_be_edited_only_within_their_course(self):
        suffix = uuid.uuid4().hex[:8].upper()
        course = client.post("/courses/", headers=_auth(self.admin), json={"title": f"Edit {suffix}", "programme_code": f"ED-{suffix}"}).json()
        other = client.post("/courses/", headers=_auth(self.admin), json={"title": f"Other {suffix}", "programme_code": f"OT-{suffix}"}).json()
        subject = client.post("/admin/subjects", headers=_auth(self.admin), json={"name": f"Biology {suffix}", "course_id": course["id"]}).json()
        changed = client.put(f"/admin/courses/{course['id']}/syllabus/subject/{subject['id']}", headers=_auth(self.admin), json={"name": f"Life Sciences {suffix}"})
        denied = client.put(f"/admin/courses/{other['id']}/syllabus/subject/{subject['id']}", headers=_auth(self.admin), json={"name": "Outside scope"})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(denied.status_code, 404, denied.text)

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
