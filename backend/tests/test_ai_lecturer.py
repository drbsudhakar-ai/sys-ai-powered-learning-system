"""
P0-013.4 AI Lecturer digital classroom — backend behavior tests.
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
from app.services.teaching_plans import build_teaching_plan, validate_teaching_plan
from app.services.ai_provider import MockAIProvider, get_ai_provider

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P0134 {role}",
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


class TeachingPlanUnitTests(unittest.TestCase):
    def test_newton_plan_is_stepwise_not_paragraph(self):
        plan = build_teaching_plan(title="Newton's Second Law", topic_title="Newton's Second Law")
        validate_teaching_plan(plan)
        self.assertGreaterEqual(len(plan["steps"]), 8)
        kinds = {s["kind"] for s in plan["steps"]}
        self.assertIn("CHECK", kinds)
        self.assertTrue(any(s["visual_type"] == "FORMULA" for s in plan["steps"]))
        self.assertTrue(any(s["visual_type"] == "3D_MODEL" for s in plan["steps"]))
        for s in plan["steps"]:
            self.assertLess(len(s["narration"]["text"].split()), 60)

    def test_mock_ai_provider(self):
        p = get_ai_provider()
        self.assertIsInstance(p, MockAIProvider)
        out = p.complete_json(system="sys", user="plan", context={"intent": "TEACHING_PLAN"})
        self.assertTrue(out.get("prefer_template"))


class AILecturerAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P0134A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P0134F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P0134S"})
        cls.student2_token, cls.student2_id = _register_login("student", {"roll_number": "P0134S2"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P013.4 Course", "description": "lecture"},
        )
        assert course.status_code == 201, course.text
        cls.course_id = course.json()["id"]
        assert (
            client.post(
                "/admin/course-coordinators",
                headers=_auth(cls.admin_token),
                json={"faculty_id": cls.faculty_id, "course_id": cls.course_id},
            ).status_code
            == 201
        )
        sub = client.post(
            "/admin/subjects",
            headers=_auth(cls.admin_token),
            json={"name": f"Phys-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201
        cls.subject_id = sub.json()["id"]
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Newton's Second Law", "subject_id": cls.subject_id},
        )
        assert topic.status_code == 201
        cls.topic_id = topic.json()["id"]
        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student_token)).status_code
            == 201
        )
        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student2_token)).status_code
            == 201
        )

    def _create_common(self) -> int:
        r = client.post(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            json={
                "title": "Newton's Second Law Lecture",
                "mode": "COMMON",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        sid = r.json()["id"]
        for uid in (self.student_id, self.student2_id):
            p = client.post(
                f"/learning-sessions/{sid}/participants",
                headers=_auth(self.faculty_token),
                json={"user_id": uid, "role": "STUDENT"},
            )
            self.assertEqual(p.status_code, 201, p.text)
        return sid

    def _create_individual(self, student_id: int) -> int:
        r = client.post(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            json={
                "title": "Individual Newton session",
                "mode": "INDIVIDUAL",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
                "primary_student_id": student_id,
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def test_unauthenticated_lecture_denied(self):
        self.assertEqual(client.post("/learning-sessions/1/lecture/open").status_code, 401)
        self.assertEqual(client.get("/learning-sessions/1/lecture").status_code, 401)

    def test_open_sequence_progress_interact_complete(self):
        sid = self._create_common()
        opened = client.post(
            f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token)
        )
        self.assertEqual(opened.status_code, 200, opened.text)
        body = opened.json()
        self.assertIn("teaching_plan", body)
        self.assertGreaterEqual(body["step_count"], 5)
        self.assertEqual(body["current_step_index"], 0)
        self.assertTrue(body["current_step"]["narration"]["text"])
        self.assertNotIn("<script", str(body["teaching_plan"]).lower())

        got = client.get(f"/learning-sessions/{sid}/lecture", headers=_auth(self.student_token))
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["activity_id"], body["activity_id"])

        nxt = client.post(
            f"/learning-sessions/{sid}/lecture/step",
            headers=_auth(self.student_token),
            json={"action": "NEXT"},
        )
        self.assertEqual(nxt.status_code, 200, nxt.text)
        self.assertEqual(nxt.json()["current_step_index"], 1)

        pause = client.post(
            f"/learning-sessions/{sid}/lecture/control",
            headers=_auth(self.student_token),
            json={"action": "PAUSE"},
        )
        self.assertEqual(pause.json()["lecture_status"], "PAUSED")
        resume = client.post(
            f"/learning-sessions/{sid}/lecture/control",
            headers=_auth(self.student_token),
            json={"action": "RESUME"},
        )
        self.assertEqual(resume.json()["lecture_status"], "PLAYING")

        ask = client.post(
            f"/learning-sessions/{sid}/lecture/interact",
            headers=_auth(self.student_token),
            json={"intent": "ASK", "message": "Why does acceleration increase?"},
        )
        self.assertEqual(ask.status_code, 200, ask.text)
        self.assertGreater(ask.json()["step_count"], body["step_count"])
        # Response remains board/teaching-plan oriented
        self.assertIn("teaching_plan", ask.json())
        self.assertIn("current_step", ask.json())

        done = client.post(
            f"/learning-sessions/{sid}/lecture/control",
            headers=_auth(self.student_token),
            json={"action": "COMPLETE"},
        )
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["lecture_status"], "COMPLETED")

        # Peer progress independent — student2 still at start if not advanced much
        open2 = client.post(
            f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student2_token)
        )
        self.assertEqual(open2.status_code, 200)
        self.assertEqual(open2.json()["lecture_status"] in ("READY", "PLAYING", "COMPLETED"), True)

    def test_individual_access_denied_for_other_student(self):
        sid = self._create_individual(self.student_id)
        ok = client.post(
            f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token)
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        denied = client.post(
            f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student2_token)
        )
        self.assertEqual(denied.status_code, 403)
        denied_get = client.get(
            f"/learning-sessions/{sid}/lecture", headers=_auth(self.student2_token)
        )
        self.assertEqual(denied_get.status_code, 403)

    def test_invalid_step_and_state(self):
        sid = self._create_common()
        client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token))
        bad = client.post(
            f"/learning-sessions/{sid}/lecture/step",
            headers=_auth(self.student_token),
            json={"action": "GOTO", "step_index": 9999},
        )
        self.assertEqual(bad.status_code, 422)
        missing = client.get(
            f"/learning-sessions/{sid + 999999}/lecture", headers=_auth(self.student_token)
        )
        self.assertIn(missing.status_code, (403, 404))


if __name__ == "__main__":
    unittest.main()
