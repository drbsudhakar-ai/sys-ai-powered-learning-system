"""P0-018 Course & Programme Foundation Alignment tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app.constants import PROGRAMME_CATEGORIES, PROGRAMME_CODE_ENGLISH_COMMUNICATION

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P018 {role}",
        "email": email,
        "role": role,
        "password": "TestPass123!",
        **extra,
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post("/auth/login", data={"username": email, "password": "TestPass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"], reg.json()["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class ProgrammeFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P018A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P018F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P018S"})
        cls.other_token, cls.other_id = _register_login("student", {"roll_number": "P018X"})
        cls.unenrolled_token, cls.unenrolled_id = _register_login("student", {"roll_number": "P018U"})

    def _create(self, token: str, **fields):
        payload = {"title": fields.pop("title", f"P018 {uuid.uuid4().hex[:6]}"), **fields}
        return client.post("/courses/", headers=_auth(token), json=payload)

    def test_create_supported_categories_and_retrieve(self):
        for cat in PROGRAMME_CATEGORIES:
            res = self._create(
                self.admin_token,
                title=f"P018 {cat}",
                programme_category=cat,
                examination_name="NEET" if cat == "HIGHER_EDUCATION_ENTRANCE" else None,
                examination_authority="NTA" if cat == "HIGHER_EDUCATION_ENTRANCE" else None,
                target_purpose="Entrance preparation" if cat == "HIGHER_EDUCATION_ENTRANCE" else "Learning",
            )
            self.assertEqual(res.status_code, 201, res.text)
            body = res.json()
            self.assertEqual(body["programme_category"], cat)
            self.assertTrue(body["is_active"])
            got = client.get(f"/courses/{body['id']}", headers=_auth(self.student_token))
            self.assertEqual(got.status_code, 200)
            self.assertEqual(got.json()["programme_category"], cat)

    def test_update_classification_and_reject_invalid(self):
        created = self._create(self.faculty_token, title="P018 Update Cat", programme_category="EMPLOYMENT_EXAM")
        self.assertEqual(created.status_code, 201, created.text)
        cid = created.json()["id"]
        upd = client.put(
            f"/courses/{cid}",
            headers=_auth(self.faculty_token),
            json={"programme_category": "SKILL_DEVELOPMENT"},
        )
        self.assertEqual(upd.status_code, 200, upd.text)
        self.assertEqual(upd.json()["programme_category"], "SKILL_DEVELOPMENT")
        # title-only update must not reset classification
        title_only = client.put(
            f"/courses/{cid}",
            headers=_auth(self.faculty_token),
            json={"title": "P018 Still Skill"},
        )
        self.assertEqual(title_only.status_code, 200)
        self.assertEqual(title_only.json()["programme_category"], "SKILL_DEVELOPMENT")

        bad = self._create(self.admin_token, title="P018 Bad", programme_category="DEGREE_COURSE")
        self.assertEqual(bad.status_code, 422)

        bad_upd = client.put(
            f"/courses/{cid}",
            headers=_auth(self.faculty_token),
            json={"programme_category": "NOT_A_CATEGORY"},
        )
        self.assertEqual(bad_upd.status_code, 422)

    def test_existing_create_payload_still_works(self):
        res = self._create(self.faculty_token, title="P018 Legacy Payload", description="no category sent")
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["programme_category"], "INDEPENDENT_LEARNING")
        self.assertTrue(res.json()["is_active"])

    def test_multiple_and_zero_enrollments(self):
        a = self._create(
            self.admin_token,
            title="P018 NEET",
            programme_category="HIGHER_EDUCATION_ENTRANCE",
            examination_name="NEET",
        )
        b = self._create(
            self.admin_token,
            title="P018 SSC",
            programme_category="EMPLOYMENT_EXAM",
            examination_name="SSC CGL",
        )
        self.assertEqual(a.status_code, 201)
        self.assertEqual(b.status_code, 201)
        e1 = client.post(f"/courses/{a.json()['id']}/enroll", headers=_auth(self.student_token))
        e2 = client.post(f"/courses/{b.json()['id']}/enroll", headers=_auth(self.student_token))
        self.assertEqual(e1.status_code, 201, e1.text)
        self.assertEqual(e2.status_code, 201, e2.text)
        mine = client.get("/courses/me", headers=_auth(self.student_token))
        self.assertEqual(mine.status_code, 200)
        ids = {row["id"] for row in mine.json()["enrollments"]}
        self.assertIn(a.json()["id"], ids)
        self.assertIn(b.json()["id"], ids)
        self.assertFalse(mine.json()["enrollment_required"])

        none = client.get("/courses/me", headers=_auth(self.unenrolled_token))
        self.assertEqual(none.status_code, 200)
        self.assertEqual(none.json()["enrollments"], [])
        self.assertEqual(none.json()["student_id"], self.unenrolled_id)

    def test_english_communication_independent_of_exam_course(self):
        eng = self._create(
            self.admin_token,
            title="English Communication",
            programme_category="INDEPENDENT_LEARNING",
            programme_code=PROGRAMME_CODE_ENGLISH_COMMUNICATION,
            target_purpose="Independent English Communication learning",
        )
        self.assertEqual(eng.status_code, 201, eng.text)
        cid = eng.json()["id"]
        self.assertEqual(eng.json()["programme_code"], PROGRAMME_CODE_ENGLISH_COMMUNICATION)

        wrong = self._create(
            self.admin_token,
            title="English as exam",
            programme_category="HIGHER_EDUCATION_ENTRANCE",
            programme_code=PROGRAMME_CODE_ENGLISH_COMMUNICATION,
        )
        self.assertEqual(wrong.status_code, 422)

        enroll = client.post(f"/courses/{cid}/enroll", headers=_auth(self.other_token))
        self.assertEqual(enroll.status_code, 201, enroll.text)
        mine = client.get("/courses/me", headers=_auth(self.other_token))
        self.assertEqual(len(mine.json()["enrollments"]), 1)
        self.assertEqual(mine.json()["enrollments"][0]["programme_code"], PROGRAMME_CODE_ENGLISH_COMMUNICATION)
        listed = client.get(
            "/courses/",
            headers=_auth(self.other_token),
            params={"programme_code": PROGRAMME_CODE_ENGLISH_COMMUNICATION},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(c["id"] == cid for c in listed.json()))

    def test_universal_support_without_enrollment(self):
        me = client.get("/auth/me", headers=_auth(self.unenrolled_token))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["id"], self.unenrolled_id)

        inbox = client.get("/inbox/notifications", headers=_auth(self.unenrolled_token))
        self.assertEqual(inbox.status_code, 200)
        self.assertIsInstance(inbox.json(), list)

        programmes = client.get("/courses/me", headers=_auth(self.unenrolled_token))
        self.assertEqual(programmes.status_code, 200)
        support = programmes.json()["universal_support"]
        self.assertTrue(support["available"])
        self.assertFalse(support["requires_course_enrollment"])
        self.assertIn("/notifications", support["entry_points"])

    def test_student_cannot_see_peer_programme_enrollments(self):
        course = self._create(self.admin_token, title="P018 Private", programme_category="EMPLOYMENT_EXAM")
        cid = course.json()["id"]
        self.assertEqual(
            client.post(f"/courses/{cid}/enroll", headers=_auth(self.student_token)).status_code,
            201,
        )
        peer = client.get("/courses/me", headers=_auth(self.unenrolled_token))
        self.assertEqual(peer.status_code, 200)
        self.assertFalse(any(r["id"] == cid for r in peer.json()["enrollments"]))

    def test_student_cannot_create_and_faculty_write_still_works(self):
        denied = self._create(self.student_token, title="P018 Student Create")
        self.assertEqual(denied.status_code, 403)
        ok = self._create(self.faculty_token, title="P018 Faculty Still")
        self.assertEqual(ok.status_code, 201)

    def test_inactive_programme_blocks_enroll(self):
        res = self._create(
            self.admin_token,
            title="P018 Inactive",
            programme_category="SKILL_DEVELOPMENT",
            is_active=False,
        )
        self.assertEqual(res.status_code, 201)
        enroll = client.post(f"/courses/{res.json()['id']}/enroll", headers=_auth(self.student_token))
        self.assertEqual(enroll.status_code, 409)


if __name__ == "__main__":
    unittest.main()
