"""
P0-012 Performance Analyzer + Unified Notification Engine tests.
Uses real P0-011 evaluated attempts (not fixture-only analyzer input).
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
from app import models, database

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P012 {role}",
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


class PerformanceAnalyzerNotifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P012A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P012F"})
        cls.expert_token, cls.expert_id = _register_login("faculty", {"employee_code": "P012E"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P012S"})
        cls.other_student_token, cls.other_student_id = _register_login(
            "student", {"roll_number": "P012S2"}
        )

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P012 Course", "description": "analyzer"},
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
        assert (
            client.post(
                "/admin/subject-experts",
                headers=_auth(cls.admin_token),
                json={"faculty_id": cls.expert_id, "subject_id": cls.subject_id},
            ).status_code
            == 201
        )
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Mechanics", "subject_id": cls.subject_id},
        )
        assert topic.status_code == 201
        cls.topic_id = topic.json()["id"]

        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student_token)).status_code
            == 201
        )

    def _seed_q(self, stem, difficulty, correct, tags=None):
        q = client.post(
            "/question-bank/questions",
            headers=_auth(self.admin_token),
            json={
                "stem": stem,
                "difficulty": difficulty,
                "status": "ACTIVE",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
                "options": ["A", "B", "C", "D"],
                "correct_answer": correct,
                "explanation": "Why",
                "concept_tags": tags or ["Newton"],
                "marks": 2,
                "negative_marks": -0.5,
            },
        )
        self.assertEqual(q.status_code, 201, q.text)
        return q.json()

    def _publish_and_complete(self, assessment_type="TOPIC_TEST", title=None, wrong=False):
        title = title or f"{assessment_type} {uuid.uuid4().hex[:6]}"
        self._seed_q(f"{title} EASY {uuid.uuid4().hex[:4]}", "EASY", "A")
        self._seed_q(f"{title} MED {uuid.uuid4().hex[:4]}", "MEDIUM", "B")
        self._seed_q(f"{title} HARD {uuid.uuid4().hex[:4]}", "HARD", "C")

        payload = {
            "title": title,
            "course_id": self.course_id,
            "assessment_type": assessment_type,
            "duration_minutes": 30,
            "total_questions": 3,
            "total_marks": 6,
            "marks_correct": 2,
            "marks_incorrect": -0.5,
            "max_attempts": 3,
        }
        if assessment_type == "TOPIC_TEST":
            payload["subject_id"] = self.subject_id
            payload["topic_id"] = self.topic_id

        created = client.post("/assessments/", headers=_auth(self.faculty_token), json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        aid = created.json()["id"]
        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=_auth(self.faculty_token),
            json=[
                {"subject_id": self.subject_id, "topic_id": self.topic_id, "difficulty": "EASY", "question_count": 1},
                {"subject_id": self.subject_id, "topic_id": self.topic_id, "difficulty": "MEDIUM", "question_count": 1},
                {"subject_id": self.subject_id, "topic_id": self.topic_id, "difficulty": "HARD", "question_count": 1},
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)
        pub = client.post(f"/assessments/{aid}/publish", headers=_auth(self.faculty_token))
        self.assertEqual(pub.status_code, 200, pub.text)
        version_id = pub.json()["version_id"]

        start = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(start.status_code, 201, start.text)
        attempt_id = start.json()["attempt_id"]
        att = client.get(f"/student/attempts/{attempt_id}", headers=_auth(self.student_token))
        questions = att.json()["questions"]

        db = database.SessionLocal()
        try:
            snaps = {
                aq.id: aq
                for aq in db.query(models.AssessmentQuestion)
                .filter(models.AssessmentQuestion.version_id == version_id)
                .all()
            }
        finally:
            db.close()

        for q in questions:
            snap = snaps[q["assessment_question_id"]]
            ans = snap.correct_answer_snapshot
            if wrong:
                opts = snap.options_snapshot or ["A", "B", "C", "D"]
                ans = next(o for o in opts if o != snap.correct_answer_snapshot)
            r = client.post(
                f"/student/attempts/{attempt_id}/responses",
                headers=_auth(self.student_token),
                json={
                    "assessment_question_id": q["assessment_question_id"],
                    "selected_answer": ans,
                    "time_spent_delta": 40,
                },
            )
            self.assertEqual(r.status_code, 200, r.text)

        submit = client.post(f"/student/attempts/{attempt_id}/submit", headers=_auth(self.student_token))
        self.assertEqual(submit.status_code, 200, submit.text)
        self.assertEqual(submit.json()["status"], "EVALUATED")
        return aid, attempt_id, version_id, submit.json()

    def test_real_attempt_feeds_analyzer_and_notifications(self):
        # Mix of assessment types via real submits
        self._publish_and_complete("TOPIC_TEST", wrong=False)
        self._publish_and_complete("WEEKLY_TEST", wrong=True)
        self._publish_and_complete("MONTHLY_TEST", wrong=True)

        analysis = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}",
            headers=_auth(self.student_token),
            params={"refresh": True},
        )
        self.assertEqual(analysis.status_code, 200, analysis.text)
        body = analysis.json()
        self.assertIn("overall", body)
        self.assertIn("subject_performance", body)
        self.assertIn("topic_performance", body)
        self.assertIn("difficulty_performance", body)
        self.assertIn("assessment_type_performance", body)
        self.assertIn("trends", body)
        self.assertIn("learning_gaps", body)
        self.assertIn("readiness", body)
        self.assertEqual(body["readiness"]["label"], "ANALYTICAL_ESTIMATE")
        types = {r["assessment_type"] for r in body["assessment_type_performance"]}
        self.assertIn("TOPIC_TEST", types)
        self.assertIn("WEEKLY_TEST", types)
        self.assertIn("MONTHLY_TEST", types)
        # Evidence vs inference present on gaps/scopes
        for s in body["subject_performance"]:
            self.assertEqual(s["observed_evidence"]["kind"], "OBSERVED_EVIDENCE")
            self.assertEqual(s["system_inference"]["kind"], "SYSTEM_INFERENCE")

        profile = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}/profile",
            headers=_auth(self.student_token),
        )
        self.assertEqual(profile.status_code, 200)
        self.assertIn("ai_lecturer_contract", profile.json())
        self.assertEqual(profile.json()["evidence"]["source"], "P0-011_EVALUATED_ATTEMPTS")

        gaps = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}/gaps",
            headers=_auth(self.student_token),
        )
        self.assertEqual(gaps.status_code, 200)

        readiness = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}/readiness",
            headers=_auth(self.student_token),
        )
        self.assertEqual(readiness.status_code, 200)
        self.assertIn("disclaimer", readiness.json())

        report = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}/report",
            headers=_auth(self.student_token),
        )
        self.assertEqual(report.status_code, 200)
        self.assertIn("disclaimer", report.json())

        pdf = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}/report.pdf",
            headers=_auth(self.student_token),
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn(b"SYS", pdf.content)

        # In-app notifications for student
        inbox = client.get("/inbox/notifications", headers=_auth(self.student_token))
        self.assertEqual(inbox.status_code, 200)
        self.assertGreater(len(inbox.json()), 0)
        events = {n["event"] for n in inbox.json()}
        self.assertTrue("RESULT_AVAILABLE" in events or "PERFORMANCE_ANALYSIS_AVAILABLE" in events)

        unread = client.get("/inbox/unread-count", headers=_auth(self.student_token))
        self.assertEqual(unread.status_code, 200)
        self.assertGreaterEqual(unread.json()["unread"], 0)

        delivery_id = inbox.json()[0]["delivery_id"]
        marked = client.post(
            f"/inbox/notifications/{delivery_id}/read", headers=_auth(self.student_token)
        )
        self.assertEqual(marked.status_code, 200)

        # Faculty/coordinator/admin/expert can view
        for token in (self.faculty_token, self.admin_token, self.expert_token):
            r = client.get(
                f"/analyzer/students/{self.student_id}/courses/{self.course_id}",
                headers=_auth(token),
            )
            self.assertEqual(r.status_code, 200, r.text)

        # Cross-student blocked
        denied = client.get(
            f"/analyzer/students/{self.student_id}/courses/{self.course_id}",
            headers=_auth(self.other_student_token),
        )
        self.assertEqual(denied.status_code, 403)

        # Preferences
        prefs = client.get("/inbox/preferences", headers=_auth(self.student_token))
        self.assertEqual(prefs.status_code, 200)
        self.assertTrue(prefs.json())
        upd = client.put(
            "/inbox/preferences",
            headers=_auth(self.student_token),
            json=[{"category": "ROUTINE", "email_enabled": False, "in_app_enabled": True}],
        )
        self.assertEqual(upd.status_code, 200)

        # Audit / retry path for admin
        notes = client.get("/notifications", headers=_auth(self.admin_token))
        self.assertEqual(notes.status_code, 200)
        self.assertGreater(len(notes.json()), 0)
        nid = notes.json()[0]["id"]
        retry = client.post(f"/notifications/{nid}/retry", headers=_auth(self.admin_token))
        self.assertEqual(retry.status_code, 200)

        # DB integrity: performance analysis + deliveries exist
        db = database.SessionLocal()
        try:
            pa = (
                db.query(models.PerformanceAnalysis)
                .filter(
                    models.PerformanceAnalysis.student_id == self.student_id,
                    models.PerformanceAnalysis.course_id == self.course_id,
                )
                .first()
            )
            self.assertIsNotNone(pa)
            self.assertTrue(pa.analysis_json)
            deliveries = db.query(models.NotificationDelivery).filter(
                models.NotificationDelivery.user_id == self.student_id
            ).count()
            self.assertGreater(deliveries, 0)
            profile_row = (
                db.query(models.StudentLearningProfile)
                .filter(
                    models.StudentLearningProfile.student_id == self.student_id,
                    models.StudentLearningProfile.course_id == self.course_id,
                )
                .first()
            )
            self.assertIsNotNone(profile_row)
        finally:
            db.close()

    def test_unauthenticated_blocked(self):
        self.assertEqual(client.get("/analyzer/me?course_id=1").status_code, 401)
        self.assertEqual(client.get("/inbox/notifications").status_code, 401)


if __name__ == "__main__":
    unittest.main()
