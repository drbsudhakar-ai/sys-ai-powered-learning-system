"""
P0-017 Personalized Learning Journey & Learning Orchestration tests.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app import models, database
from app.services.learning_orchestrator import (
    alternatives_for,
    build_candidates,
    daily_plan_from,
    derive_journey_state,
    select_next_best,
)

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P017 {role}",
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


def _base_snapshot(**over):
    snap = {
        "course_id": 1,
        "topics": {},
        "states": {},
        "active_gaps": [],
        "open_interventions": [],
        "open_sessions": [],
        "lecture_resume": None,
        "open_attempts": [],
        "assignments": [],
        "events_by_topic": {},
        "warnings": [],
        "published_assessments": [],
        "next_topic": None,
        "faculty_actions": [],
        "now": datetime.now(timezone.utc),
    }
    snap.update(over)
    return snap


class OrchestratorUnitTests(unittest.TestCase):
    def test_remediation_outranks_practice(self):
        topic = SimpleNamespace(id=10, name="Newton's Laws", subject_id=2)
        state = SimpleNamespace(status="NEEDS_PRACTICE", topic_id=10)
        gap = SimpleNamespace(
            id=5,
            scope_type="TOPIC",
            scope_id=10,
            classification="WEAK",
            inference={},
        )
        iv = SimpleNamespace(
            id=9,
            priority_explanation="Assigned remedial session",
            learning_gap=gap,
            gap_snapshot={"scope_name": "Newton's Laws", "classification": "WEAK", "scope_id": 10},
            learning_session_id=3,
        )
        cands = build_candidates(
            _base_snapshot(
                topics={10: topic},
                states={10: state},
                active_gaps=[gap],
                open_interventions=[iv],
            )
        )
        nxt = select_next_best(cands)
        self.assertEqual(nxt["action_type"], "COMPLETE_REMEDIATION")
        self.assertEqual(nxt["source"], "P0-014")
        self.assertIn("what", nxt["explanation"])
        self.assertIn("why", nxt["explanation"])
        self.assertIn("source", nxt["explanation"])
        self.assertIn("outcome", nxt["explanation"])

    def test_mastery_aware_reassessment(self):
        topic = SimpleNamespace(id=4, name="Integration", subject_id=1)
        state = SimpleNamespace(status="READY_FOR_REASSESSMENT", topic_id=4)
        cands = build_candidates(_base_snapshot(topics={4: topic}, states={4: state}))
        nxt = select_next_best(cands)
        self.assertEqual(nxt["action_type"], "TAKE_REASSESSMENT")
        self.assertEqual(nxt["source"], "P0-015")

    def test_failed_reassessment_follow_up(self):
        topic = SimpleNamespace(id=4, name="Integration", subject_id=1)
        state = SimpleNamespace(status="NEEDS_PRACTICE", topic_id=4)
        ev = SimpleNamespace(event_type="REASSESSMENT_FAILED")
        cands = build_candidates(
            _base_snapshot(
                topics={4: topic},
                states={4: state},
                events_by_topic={4: [ev]},
            )
        )
        types = [c["action_type"] for c in cands]
        self.assertIn("RETRY", types)
        nxt = select_next_best(cands)
        self.assertEqual(nxt["action_type"], "RETRY")

    def test_early_warning_urgent_recommends_human_support(self):
        topic = SimpleNamespace(id=7, name="Kinematics", subject_id=1)
        state = SimpleNamespace(status="NEEDS_REMEDIATION", topic_id=7)
        cands = build_candidates(
            _base_snapshot(
                topics={7: topic},
                states={7: state},
                warnings=[
                    {
                        "code": "PERSISTENT_LEARNING_GAP",
                        "severity": "URGENT_ATTENTION",
                        "topic_id": 7,
                        "reason": "Persistent gap",
                    }
                ],
            )
        )
        nxt = select_next_best(cands)
        self.assertEqual(nxt["action_type"], "HUMAN_EXPERT_SUPPORT")
        self.assertEqual(nxt["source"], "P0-016")

    def test_unfinished_attempt_is_critical(self):
        assessment = SimpleNamespace(
            title="Weekly Test",
            assessment_type="WEEKLY_TEST",
            topic_id=1,
            subject_id=1,
        )
        att = SimpleNamespace(id=22, assessment=assessment, assessment_id=88)
        cands = build_candidates(_base_snapshot(open_attempts=[att]))
        nxt = select_next_best(cands)
        self.assertEqual(nxt["priority"], "CRITICAL")
        self.assertTrue(nxt["mandatory"])

    def test_daily_plan_from_actions_not_scheduler(self):
        cands = build_candidates(
            _base_snapshot(
                topics={1: SimpleNamespace(id=1, name="T", subject_id=1)},
                states={1: SimpleNamespace(status="NEEDS_PRACTICE", topic_id=1)},
            )
        )
        plan = daily_plan_from(cands)
        self.assertGreaterEqual(len(plan), 1)
        self.assertLessEqual(len(plan), 4)

    def test_alternatives_include_self_study(self):
        topic = SimpleNamespace(id=2, name="Optics", subject_id=1)
        state = SimpleNamespace(status="NOT_ASSESSED", topic_id=2)
        cands = build_candidates(_base_snapshot(topics={2: topic}, states={2: state}))
        nxt = select_next_best(cands)
        alts = alternatives_for(nxt, cands)
        self.assertTrue(any(a["action_type"] == "SELF_STUDY" for a in alts))

    def test_journey_state_mastered(self):
        st = SimpleNamespace(status="MASTERED")
        self.assertEqual(derive_journey_state({"states": {1: st}, "topics": {1: 1}}, None), "MASTERED")

    def test_deterministic_order(self):
        topic = SimpleNamespace(id=3, name="X", subject_id=1)
        state = SimpleNamespace(status="LEARNING", topic_id=3)
        snap = _base_snapshot(topics={3: topic}, states={3: state})
        a = [c["stable_key"] for c in build_candidates(snap)]
        b = [c["stable_key"] for c in build_candidates(snap)]
        self.assertEqual(a, b)


class LearningJourneyAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P017A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P017F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P017S"})
        cls.other_token, cls.other_id = _register_login("student", {"roll_number": "P017X"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P017 Course", "description": "journey"},
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
            json={"name": f"PHY-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201
        cls.subject_id = sub.json()["id"]
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Newton's Laws", "subject_id": cls.subject_id},
        )
        assert topic.status_code == 201
        cls.topic_id = topic.json()["id"]
        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student_token)).status_code
            == 201
        )
        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.other_token)).status_code
            == 201
        )

        db = database.SessionLocal()
        try:
            db.add(
                models.LearningGap(
                    student_id=cls.student_id,
                    course_id=cls.course_id,
                    scope_type="TOPIC",
                    scope_id=cls.topic_id,
                    scope_name="Newton's Laws",
                    classification="WEAK",
                    confidence=0.8,
                    priority_score=70,
                    is_high_priority=True,
                )
            )
            db.add(
                models.TopicMasteryState(
                    student_id=cls.student_id,
                    course_id=cls.course_id,
                    topic_id=cls.topic_id,
                    subject_id=cls.subject_id,
                    status="NEEDS_PRACTICE",
                    indicator="YELLOW",
                    practice_accuracy=62.0,
                )
            )
            db.commit()
        finally:
            db.close()

    def test_student_journey_next_action(self):
        res = client.get(
            "/learning-journey/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("next_best_action", data)
        self.assertIsNotNone(data["next_best_action"])
        expl = data["next_best_action"]["explanation"]
        self.assertTrue(expl.get("what") and expl.get("why") and expl.get("source") and expl.get("outcome"))
        self.assertIn("P0-017 selects", data["authority_note"])

    def test_no_cross_student_leakage(self):
        res = client.get(
            f"/learning-journey/faculty/students/{self.student_id}",
            headers=_auth(self.other_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 403)

        mine = client.get(
            "/learning-journey/me",
            headers=_auth(self.other_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(mine.status_code, 200, mine.text)
        self.assertEqual(mine.json()["student_id"], self.other_id)

    def test_action_lifecycle_complete_and_supersede(self):
        res = client.get(
            "/learning-journey/me/actions",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        actions = res.json()["actions"]
        self.assertTrue(actions)
        optional = next((a for a in actions if not a.get("mandatory") and a["action_type"] == "SELF_STUDY"), None)
        if optional:
            d = client.post(
                f"/learning-journey/me/actions/{optional['action_id']}/dismiss",
                headers=_auth(self.student_token),
            )
            self.assertEqual(d.status_code, 200, d.text)
            self.assertEqual(d.json()["status"], "CANCELLED")

        primary = res.json()["next_best_action"]
        done = client.post(
            f"/learning-journey/me/actions/{primary['action_id']}/complete",
            headers=_auth(self.student_token),
        )
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["status"], "COMPLETED")

        again = client.get(
            "/learning-journey/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(again.status_code, 200)
        # Completed action is not the open primary; a new recommendation may appear
        nba = again.json()["next_best_action"]
        if nba:
            self.assertNotEqual(nba["status"], "COMPLETED")

    def test_mandatory_cannot_dismiss_remediation(self):
        db = database.SessionLocal()
        try:
            gap = (
                db.query(models.LearningGap)
                .filter(
                    models.LearningGap.student_id == self.student_id,
                    models.LearningGap.scope_id == self.topic_id,
                )
                .first()
            )
            iv = models.RemedialIntervention(
                course_id=self.course_id,
                student_id=self.student_id,
                learning_gap_id=gap.id if gap else None,
                gap_snapshot={
                    "scope_type": "TOPIC",
                    "scope_id": self.topic_id,
                    "scope_name": "Newton's Laws",
                    "classification": "WEAK",
                },
                intervention_type="GUIDED_PRACTICE",
                mode="INDIVIDUAL",
                priority_rank=1,
                priority_explanation="Assigned by test",
                plan={"steps": ["review"]},
                explanation={"why_intervention_selected": "test"},
                status="ASSIGNED",
                created_by=self.faculty_id,
            )
            db.add(iv)
            db.commit()
        finally:
            db.close()

        res = client.get(
            "/learning-journey/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        rem = next(
            (a for a in res.json()["actions"] if a["action_type"] == "COMPLETE_REMEDIATION"),
            res.json()["next_best_action"],
        )
        self.assertEqual(rem["action_type"], "COMPLETE_REMEDIATION")
        dismiss = client.post(
            f"/learning-journey/me/actions/{rem['action_id']}/dismiss",
            headers=_auth(self.student_token),
        )
        self.assertEqual(dismiss.status_code, 409)

    def test_faculty_visibility_and_recommend(self):
        res = client.get(
            "/learning-journey/faculty/students",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        students = res.json()["students"]
        self.assertTrue(any(s["student_id"] == self.student_id for s in students))
        me = next(s for s in students if s["student_id"] == self.student_id)
        self.assertTrue(me.get("next_action_title") or me.get("journey_state"))

        rec = client.post(
            f"/learning-journey/faculty/students/{self.student_id}/recommend",
            headers=_auth(self.faculty_token),
            json={
                "course_id": self.course_id,
                "action_type": "HUMAN_EXPERT_SUPPORT",
                "topic_id": self.topic_id,
                "reason": "Consider expert support for this persistent gap.",
            },
        )
        self.assertEqual(rec.status_code, 200, rec.text)
        self.assertEqual(rec.json()["source"], "FACULTY")
        self.assertNotIn("mastery_percent", rec.json())

    def test_student_cannot_see_faculty_roster(self):
        res = client.get(
            "/learning-journey/faculty/students",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_overview_aggregate_only(self):
        res = client.get(
            "/learning-journey/admin/overview",
            headers=_auth(self.admin_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("remedial_learning_demand", data)
        self.assertNotIn("students", data)
        forbidden = client.get(
            "/learning-journey/admin/overview",
            headers=_auth(self.student_token),
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_resume_learning_from_session_evidence(self):
        db = database.SessionLocal()
        try:
            sess = models.LearningSession(
                title="AI Lecturer — Newton's Laws",
                mode="INDIVIDUAL",
                status="IN_PROGRESS",
                course_id=self.course_id,
                subject_id=self.subject_id,
                topic_id=self.topic_id,
                created_by=self.faculty_id,
            )
            db.add(sess)
            db.flush()
            part = models.LearningSessionParticipant(
                session_id=sess.id,
                user_id=self.student_id,
                role="STUDENT",
                status="ACTIVE",
            )
            db.add(part)
            db.add(
                models.LearningEvidence(
                    session_id=sess.id,
                    user_id=self.student_id,
                    event_type="TEACHING_STEP_REACHED",
                    payload={"current_step_index": 5, "status": "PAUSED", "step_count": 10},
                )
            )
            db.commit()
            sid = sess.id
        finally:
            db.close()

        res = client.get(
            "/learning-journey/me/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIsNotNone(data.get("resume"))
        self.assertEqual(data["resume"]["session_id"], sid)
        self.assertEqual(data["resume"]["current_step_index"], 5)
        # Unfinished session ranks above practice
        self.assertEqual(data["next_best_action"]["action_type"], "CONTINUE_LEARNING")

    def test_notification_on_high_priority(self):
        db = database.SessionLocal()
        try:
            notes = (
                db.query(models.Notification)
                .filter(
                    models.Notification.student_id == self.student_id,
                    models.Notification.source_module == "ORCHESTRATOR",
                )
                .all()
            )
            self.assertTrue(len(notes) >= 1)
            self.assertTrue(
                all(n.event in (
                    "NEXT_LEARNING_ACTION_AVAILABLE",
                    "REASSESSMENT_READY",
                    "REMEDIAL_ACTION_REQUIRED",
                    "LEARNING_PLAN_REMINDER",
                    "SUPPORT_RECOMMENDED",
                    "MASTERY_MILESTONE",
                ) for n in notes)
            )
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
