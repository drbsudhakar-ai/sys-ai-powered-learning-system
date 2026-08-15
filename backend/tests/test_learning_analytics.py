"""P0-016 Learning Intelligence & Early-Warning tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app import models, database
from app.services import early_warning as ew
from app.services import learning_analytics as la

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P016 {role}",
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


class EarlyWarningUnitTests(unittest.TestCase):
    def test_recommend_for_status(self):
        self.assertEqual(ew.recommend_for_status("MASTERED")["action"], "CONTINUE")
        self.assertEqual(ew.recommend_for_status("READY_FOR_REASSESSMENT")["action"], "TAKE_REASSESSMENT")
        self.assertEqual(ew.recommend_for_status("NEEDS_PRACTICE")["action"], "START_PRACTICE")

    def test_warning_policy_has_thresholds(self):
        db = database.SessionLocal()
        try:
            pol = ew.get_warning_policy(db, None)
            self.assertIn("mastery_threshold", pol)
            self.assertIn("gap_persistence_days", pol)
            self.assertGreater(pol["min_evidence_count"], 0)
        finally:
            db.close()


class LearningAnalyticsAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P016A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P016F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P016S"})
        cls.other_token, cls.other_id = _register_login("student", {"roll_number": "P016X"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P016 Course", "description": "analytics"},
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
            json={"name": f"AN-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201
        cls.subject_id = sub.json()["id"]
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Recursion Analytics", "subject_id": cls.subject_id},
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
            old = datetime.now(timezone.utc) - timedelta(days=20)
            gap = models.LearningGap(
                student_id=cls.student_id,
                course_id=cls.course_id,
                scope_type="TOPIC",
                scope_id=cls.topic_id,
                scope_name="Recursion Analytics",
                classification="WEAK",
                confidence=0.9,
                priority_score=0.8,
                evidence={"accuracy": 0.45},
                is_high_priority=True,
            )
            db.add(gap)
            db.flush()
            gap.created_at = old

            state = models.TopicMasteryState(
                student_id=cls.student_id,
                course_id=cls.course_id,
                topic_id=cls.topic_id,
                subject_id=cls.subject_id,
                status="NEEDS_REMEDIATION",
                indicator="RED",
                mastery_percent=48.0,
                practice_accuracy=62.0,
                target_difficulty="EASY",
                remediation_source="SELF_STUDY",
                explanation={"note": "seed"},
            )
            db.add(state)
            db.flush()

            for et, fr, to, pct in [
                ("PRACTICE_EVALUATED", "NEEDS_REMEDIATION", "NEEDS_PRACTICE", 55.0),
                ("PRACTICE_EVALUATED", "NEEDS_PRACTICE", "LEARNING", 62.0),
                ("REASSESSMENT_FAILED", "READY_FOR_REASSESSMENT", "NEEDS_REMEDIATION", 58.0),
            ]:
                db.add(
                    models.MasteryEvent(
                        student_id=cls.student_id,
                        course_id=cls.course_id,
                        topic_id=cls.topic_id,
                        event_type=et,
                        from_status=fr,
                        to_status=to,
                        evidence={"percentage": pct, "questions": 8, "correct": 4},
                        explanation={"summary": "seed"},
                    )
                )

            # Positive mastery for other student
            db.add(
                models.TopicMasteryState(
                    student_id=cls.other_id,
                    course_id=cls.course_id,
                    topic_id=cls.topic_id,
                    subject_id=cls.subject_id,
                    status="MASTERED",
                    indicator="GREEN",
                    mastery_percent=88.0,
                    practice_accuracy=90.0,
                    remediation_source="AI_LECTURER",
                )
            )
            db.add(
                models.MasteryEvent(
                    student_id=cls.other_id,
                    course_id=cls.course_id,
                    topic_id=cls.topic_id,
                    event_type="MASTERED",
                    from_status="NEEDS_REMEDIATION",
                    to_status="MASTERED",
                    evidence={"percentage": 88.0, "questions": 10, "correct": 9},
                    explanation={"summary": "mastered", "remediation_source_affects_decision": False},
                )
            )
            db.add(
                models.MasteryEvent(
                    student_id=cls.other_id,
                    course_id=cls.course_id,
                    topic_id=cls.topic_id,
                    event_type="PRACTICE_EVALUATED",
                    from_status="NEEDS_PRACTICE",
                    to_status="READY_FOR_REASSESSMENT",
                    evidence={"percentage": 84.0},
                )
            )
            db.commit()
        finally:
            db.close()

    def test_unauthenticated(self):
        self.assertEqual(client.get("/analytics/me", params={"course_id": self.course_id}).status_code, 401)

    def test_student_cannot_view_peer(self):
        denied = client.get(
            f"/analytics/students/{self.student_id}/courses/{self.course_id}",
            headers=_auth(self.other_token),
        )
        self.assertEqual(denied.status_code, 403)

    def test_student_analytics(self):
        res = client.get(
            "/analytics/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["student_id"], self.student_id)
        self.assertIn("summary", body)
        self.assertGreaterEqual(body["summary"]["needs_support"], 1)
        self.assertTrue(any(t["topic_id"] == self.topic_id for t in body["topics"]))
        # Frontend must not invent mastery — status comes from P0-015 state
        topic = next(t for t in body["topics"] if t["topic_id"] == self.topic_id)
        self.assertEqual(topic["status"], "NEEDS_REMEDIATION")
        self.assertEqual(topic["source_of_truth"], "P0-015_TopicMasteryState")
        self.assertIn("attention", body)
        self.assertTrue(any(a.get("evidence") for a in body["attention"]))

    def test_persistent_gap_and_reassessment_failure_warnings(self):
        db = database.SessionLocal()
        try:
            signals = ew.evaluate_student_warnings(
                db, student_id=self.student_id, course_id=self.course_id
            )
        finally:
            db.close()
        codes = {s["code"] for s in signals}
        self.assertIn("PERSISTENT_LEARNING_GAP", codes)
        self.assertIn("REASSESSMENT_FAILURE", codes)
        for s in signals:
            self.assertIn(s["severity"], ("INFO", "WATCH", "ATTENTION_REQUIRED", "URGENT_ATTENTION"))
            self.assertTrue(s.get("reason"))
            self.assertTrue(s.get("evidence"))

    def test_positive_progress_signal(self):
        db = database.SessionLocal()
        try:
            signals = ew.evaluate_student_warnings(
                db, student_id=self.other_id, course_id=self.course_id
            )
        finally:
            db.close()
        self.assertTrue(any(s["code"] == "POSITIVE_PROGRESS" for s in signals))

    def test_faculty_overview_topics_attention(self):
        ov = client.get(
            "/analytics/faculty/overview",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(ov.status_code, 200, ov.text)
        self.assertEqual(ov.json()["total_students"], 2)
        self.assertIn("mastery_distribution", ov.json())

        topics = client.get(
            "/analytics/faculty/topics",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(topics.status_code, 200)
        self.assertTrue(any(t["topic_id"] == self.topic_id for t in topics.json()["topics"]))

        att = client.get(
            "/analytics/faculty/attention",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(att.status_code, 200)
        self.assertGreaterEqual(att.json()["total"], 1)
        item = att.json()["items"][0]
        self.assertIn("reason", item)
        self.assertIn("recommended_action", item)

        inter = client.get(
            "/analytics/faculty/interventions",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(inter.status_code, 200)
        self.assertIn("caveat", inter.json())

    def test_student_blocked_from_faculty(self):
        denied = client.get(
            "/analytics/faculty/overview",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(denied.status_code, 403)

    def test_admin_overview(self):
        res = client.get(
            "/analytics/admin/overview",
            headers=_auth(self.admin_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertIn("totals", res.json())
        courses = client.get("/analytics/admin/courses", headers=_auth(self.admin_token))
        self.assertEqual(courses.status_code, 200)
        trends = client.get(
            "/analytics/admin/trends",
            headers=_auth(self.admin_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(trends.status_code, 200)
        self.assertIn("event_counts", trends.json())

    def test_faculty_cannot_access_admin(self):
        denied = client.get("/analytics/admin/overview", headers=_auth(self.faculty_token))
        self.assertEqual(denied.status_code, 403)

    def test_trends_and_no_duplicate_mastery_calc(self):
        tr = client.get(
            "/analytics/me/trends",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id, "topic_id": self.topic_id},
        )
        self.assertEqual(tr.status_code, 200)
        self.assertIn("transitions", tr.json())
        # Ensure learning analytics does not invent a parallel mastery percent algorithm:
        # student overview mastery_percent matches seeded TopicMasteryState.
        db = database.SessionLocal()
        try:
            state = (
                db.query(models.TopicMasteryState)
                .filter(
                    models.TopicMasteryState.student_id == self.student_id,
                    models.TopicMasteryState.topic_id == self.topic_id,
                )
                .first()
            )
            data = la.student_analytics(
                db,
                db.query(models.User).filter(models.User.id == self.student_id).first(),
                student_id=self.student_id,
                course_id=self.course_id,
            )
            topic = next(t for t in data["topics"] if t["topic_id"] == self.topic_id)
            self.assertEqual(topic["mastery_percent"], state.mastery_percent)
        finally:
            db.close()

    def test_notify_attention(self):
        res = client.post(
            "/analytics/faculty/attention/notify",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id, "student_id": self.student_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertGreaterEqual(res.json()["emitted"], 1)


if __name__ == "__main__":
    unittest.main()
