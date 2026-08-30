"""
P0-013.4 AI Lecturer digital classroom — backend behavior tests.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from tests.auth_helpers import ProtectedUserFactory
from app import database, models
from app.main import app
from app.services.teaching_plans import build_teaching_plan, validate_teaching_plan
from app.services.ai_provider import MockAIProvider, ConfiguredAIProvider, get_ai_provider

client = TestClient(app)
_users = ProtectedUserFactory(client, "P0134")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _publish_test_course(course_id: int) -> None:
    """Move this isolated fixture course to the state required for enrollment."""
    db = database.SessionLocal()
    try:
        course = db.query(models.Course).filter(models.Course.id == course_id).one()
        course.publication_status = "PUBLISHED"
        course.is_active = True
        course.self_enrollment_enabled = True
        db.commit()
    finally:
        db.close()


class TeachingPlanUnitTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"SYS_AI_PROVIDER": "mock"}))
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

    def test_live_visuals_and_recap_are_data_only(self):
        from app.services.ai_lesson_contract import lesson_plan
        from fastapi import HTTPException
        steps = [{"title": "Force", "explanation": "A force changes motion.", "narration": "Observe the relationship.",
                  "bullets": ["Force is measured in newtons"], "formula": "F = ma", "flow": ["Force", "Acceleration"], "model_3d": "force_vectors"} for _ in range(3)]
        plan = lesson_plan({"steps": steps}, "Newton")
        self.assertEqual(plan["steps"][0]["kind"], "INTRODUCTION")
        self.assertEqual(plan["steps"][-1]["kind"], "SUMMARY")
        self.assertEqual(plan["steps"][1]["visual"]["model_type"], "force_vectors")
        self.assertTrue(any(el["type"] == "flow" for el in plan["steps"][1]["board"]["elements"]))
        steps[0]["model_3d"] = "execute_arbitrary_code"
        with self.assertRaises(HTTPException):
            lesson_plan({"steps": steps}, "Invalid")


class AILecturerAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(patch.dict(os.environ, {"SYS_AI_PROVIDER": "mock"}))
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
        _publish_test_course(cls.course_id)
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

    def test_live_shared_lesson_reuse_and_private_explanation(self):
        sid = self._create_common()
        raw = {"steps": [{"title": f"Part {i}", "explanation": "Provider concept", "narration": "Provider narration"} for i in range(3)]}
        with patch.dict(os.environ, {"SYS_AI_PROVIDER": "configured"}), patch.object(ConfiguredAIProvider, "complete_json", side_effect=[raw, {"answer": "Private clarification for this learner"}]) as provider:
            opened = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.faculty_token))
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assertEqual(opened.json()["teaching_plan"]["source"], "configured_ai")
            student = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token))
            self.assertEqual(student.status_code, 200, student.text)
            self.assertEqual(provider.call_count, 1)
            answer = client.post(f"/learning-sessions/{sid}/lecture/interact", headers=_auth(self.student_token), json={"intent": "ASK", "message": "Explain again"})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertIn("Private clarification", answer.json()["current_step"]["narration"]["text"])
            self.assertEqual(answer.json()["step_count"], 3)
            peer = client.get(f"/learning-sessions/{sid}/lecture", headers=_auth(self.student2_token))
            self.assertNotIn("Private clarification", peer.text)
            playback = client.post(f"/learning-sessions/{sid}/lecture/interact", headers=_auth(self.student_token), json={"intent": "CONTINUE"})
            self.assertEqual(playback.status_code, 200, playback.text)
            self.assertEqual(provider.call_count, 2)
            own_history = client.get(f"/learning-sessions/{sid}/lecture/questions", headers=_auth(self.student_token))
            self.assertIn("Private clarification", own_history.text)
            peer_history = client.get(f"/learning-sessions/{sid}/lecture/questions", headers=_auth(self.student2_token))
            self.assertEqual(peer_history.json()["items"], [])

    def test_open_sequence_progress_interact_complete(self):
        sid = self._create_common()
        prepared = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.faculty_token))
        self.assertEqual(prepared.status_code, 200, prepared.text)
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

        # Completion requires evidence of visiting every stage, including remediation.
        for index in range(ask.json()["step_count"]):
            visited = client.post(f"/learning-sessions/{sid}/lecture/step", headers=_auth(self.student_token), json={"action": "GOTO", "step_index": index})
            self.assertEqual(visited.status_code, 200, visited.text)
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

    def test_common_requires_faculty_preparation_and_roster_is_protected(self):
        sid = self._create_common()
        denied = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(client.get(f"/learning-sessions/{sid}/lecture/roster", headers=_auth(self.student_token)).status_code, 403)
        roster = client.get(f"/learning-sessions/{sid}/lecture/roster", headers=_auth(self.faculty_token))
        self.assertEqual(roster.status_code, 200, roster.text)
        self.assertTrue(any(row["user_id"] == self.student_id for row in roster.json()["items"]))
        self.assertNotIn("email", roster.text)
        prepared = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.faculty_token))
        self.assertEqual(prepared.status_code, 200, prepared.text)

    def test_completion_requires_visits_and_is_idempotent_after_replay(self):
        sid = self._create_individual(self.student_id)
        opened = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token))
        self.assertEqual(opened.status_code, 200, opened.text)
        blocked = client.post(f"/learning-sessions/{sid}/lecture/control", headers=_auth(self.student_token), json={"action": "COMPLETE"})
        self.assertEqual(blocked.status_code, 409)
        for index in range(opened.json()["step_count"]):
            result = client.post(f"/learning-sessions/{sid}/lecture/step", headers=_auth(self.student_token), json={"action": "GOTO", "step_index": index})
            self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json()["can_complete"])
        completed = client.post(f"/learning-sessions/{sid}/lecture/control", headers=_auth(self.student_token), json={"action": "COMPLETE"})
        self.assertTrue(completed.json()["lesson_completed"])
        replayed = client.post(f"/learning-sessions/{sid}/lecture/step", headers=_auth(self.student_token), json={"action": "REPLAY"})
        self.assertEqual(replayed.json()["lecture_status"], "PLAYING")
        self.assertTrue(replayed.json()["lesson_completed"])
        client.post(f"/learning-sessions/{sid}/lecture/control", headers=_auth(self.student_token), json={"action": "COMPLETE"})
        with database.SessionLocal() as db:
            count = db.query(models.LearningEvidence).filter_by(session_id=sid, user_id=self.student_id, event_type="ACTIVITY_COMPLETED").count()
            self.assertEqual(count, 1)

    def test_lesson_completion_does_not_complete_other_assigned_activities(self):
        sid = self._create_individual(self.student_id)
        added = client.post(f"/learning-sessions/{sid}/activities", headers=_auth(self.faculty_token), json={"activity_type": "PRACTICE", "title": "Practice task", "scope": "COMMON", "sequence": 2})
        self.assertEqual(added.status_code, 201, added.text)
        opened = client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.student_token))
        for index in range(opened.json()["step_count"]):
            client.post(f"/learning-sessions/{sid}/lecture/step", headers=_auth(self.student_token), json={"action": "GOTO", "step_index": index})
        done = client.post(f"/learning-sessions/{sid}/lecture/control", headers=_auth(self.student_token), json={"action": "COMPLETE"})
        self.assertEqual(done.status_code, 200, done.text)
        self.assertTrue(done.json()["lesson_completed"])
        self.assertNotEqual(done.json()["session_status"], "COMPLETED")

    def test_common_end_does_not_mark_students_complete(self):
        sid = self._create_common()
        client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.faculty_token))
        ended = client.post(f"/learning-sessions/{sid}/complete", headers=_auth(self.faculty_token))
        self.assertEqual(ended.status_code, 200, ended.text)
        with database.SessionLocal() as db:
            self.assertEqual(db.query(models.LearningEvidence).filter_by(session_id=sid, event_type="ACTIVITY_COMPLETED").count(), 0)

    def test_subject_expert_cannot_manage_another_subject(self):
        from app.services.learning_sessions import can_manage_learning_sessions
        expert = _users.create("faculty", {"employee_code": "E-SCOPE-" + uuid.uuid4().hex[:8]})
        with database.SessionLocal() as db:
            db.add(models.SubjectExpertAssignment(faculty_id=expert.user_id, subject_id=self.subject_id))
            other = models.Subject(course_id=self.course_id, name="Other subject " + uuid.uuid4().hex[:8])
            db.add(other); db.commit()
            user = db.get(models.User, expert.user_id)
            self.assertTrue(can_manage_learning_sessions(db, user, course_id=self.course_id, subject_id=self.subject_id))
            self.assertFalse(can_manage_learning_sessions(db, user, course_id=self.course_id, subject_id=other.id))
            self.assertFalse(can_manage_learning_sessions(db, user, course_id=self.course_id))

    def test_invalid_step_and_state(self):
        sid = self._create_common()
        client.post(f"/learning-sessions/{sid}/lecture/open", headers=_auth(self.faculty_token))
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
