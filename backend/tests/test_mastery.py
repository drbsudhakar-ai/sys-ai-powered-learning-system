"""
P0-015 Adaptive Practice & Mastery Engine tests.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from tests.auth_helpers import ProtectedUserFactory
from app.main import app
from app import models, database
from app.services.mastery_engine import evaluate_mastery_decision, next_difficulty, process_attempt_for_mastery
from app.services import mastery_engine as mastery

client = TestClient(app)
_users = ProtectedUserFactory(client, "P015")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class MasteryUnitTests(unittest.TestCase):
    def test_mastery_decision_explainable(self):
        policy = {
            "mastery_threshold": 80.0,
            "min_reassessment_questions": 5,
        }
        ok = evaluate_mastery_decision(percentage=86, questions=10, correct=9, policy=policy)
        self.assertTrue(ok["mastered"])
        self.assertEqual(ok["decision"], "MASTERED")
        self.assertIn("80", ok["explanation"]["summary"])

        fail = evaluate_mastery_decision(percentage=60, questions=10, correct=6, policy=policy)
        self.assertFalse(fail["mastered"])
        self.assertEqual(fail["decision"], "GAP_PERSISTS")

        thin = evaluate_mastery_decision(percentage=90, questions=2, correct=2, policy=policy)
        self.assertFalse(thin["mastered"])
        self.assertEqual(thin["decision"], "INSUFFICIENT_EVIDENCE")

    def test_adaptive_difficulty_rules(self):
        d, reason = next_difficulty("EASY", accuracy_pct=85, practice_threshold=70)
        self.assertEqual(d, "MEDIUM")
        self.assertIn("increase", reason.lower())
        d2, _ = next_difficulty("MEDIUM", accuracy_pct=40, practice_threshold=70)
        self.assertEqual(d2, "EASY")


class MasteryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P015A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P015F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P015S"})
        cls.other_token, cls.other_id = _register_login("student", {"roll_number": "P015X"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P015 Course", "description": "mastery"},
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
            json={"name": f"CS-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201
        cls.subject_id = sub.json()["id"]
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Binary Tree Traversal", "subject_id": cls.subject_id},
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

        # Seed enough ACTIVE questions across difficulties
        for i, diff in enumerate(["EASY"] * 4 + ["MEDIUM"] * 4 + ["HARD"] * 2):
            q = client.post(
                "/question-bank/questions",
                headers=_auth(cls.admin_token),
                json={
                    "stem": f"P015 traversal Q{i} {uuid.uuid4().hex[:6]}",
                    "question_type": "SINGLE_MCQ",
                    "difficulty": diff,
                    "status": "ACTIVE",
                    "course_id": cls.course_id,
                    "subject_id": cls.subject_id,
                    "topic_id": cls.topic_id,
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Traverse correctly",
                    "marks": 1,
                    "negative_marks": 0,
                },
            )
            assert q.status_code == 201, q.text

        db = database.SessionLocal()
        try:
            db.add(
                models.LearningGap(
                    student_id=cls.student_id,
                    course_id=cls.course_id,
                    scope_type="TOPIC",
                    scope_id=cls.topic_id,
                    scope_name="Binary Tree Traversal",
                    classification="WEAK",
                    confidence=0.8,
                    priority_score=0.7,
                    evidence={"accuracy": 0.4},
                    is_high_priority=True,
                )
            )
            db.commit()
        finally:
            db.close()

    def test_unauthenticated_and_privacy(self):
        self.assertEqual(
            client.get(f"/mastery/students/{self.student_id}/courses/{self.course_id}").status_code,
            401,
        )
        denied = client.get(
            f"/mastery/students/{self.student_id}/courses/{self.course_id}",
            headers=_auth(self.other_token),
        )
        self.assertEqual(denied.status_code, 403)

    def test_policy_configurable(self):
        pol = client.put(
            "/mastery/policy",
            headers=_auth(self.faculty_token),
            json={
                "course_id": self.course_id,
                "mastery_threshold": 80,
                "practice_threshold": 70,
                "reassessment_threshold": 80,
                "min_reassessment_questions": 5,
            },
        )
        self.assertEqual(pol.status_code, 200, pol.text)
        self.assertEqual(pol.json()["mastery_threshold"], 80)

    def test_self_study_pathway_without_remediation(self):
        # Isolate from other tests that may have already mastered this topic
        db = database.SessionLocal()
        try:
            state = mastery._get_or_create_state(
                db,
                student_id=self.student_id,
                course_id=self.course_id,
                topic_id=self.topic_id,
            )
            state.status = "NEEDS_REMEDIATION"
            state.indicator = "RED"
            state.mastery_percent = 40.0
            state.eligibility_flags = {}
            state.remediation_source = None
            db.commit()
        finally:
            db.close()

        ready = client.post(
            "/mastery/reassessment/declare-ready",
            headers=_auth(self.student_token),
            json={
                "course_id": self.course_id,
                "topic_id": self.topic_id,
                "remediation_source": "SELF_STUDY",
            },
        )
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertTrue(ready.json()["eligible"])
        self.assertTrue(any("self" in r.lower() or "declared" in r.lower() for r in ready.json()["reasons"]))

        # Human expert pathway also works
        ready2 = client.post(
            "/mastery/reassessment/declare-ready",
            headers=_auth(self.student_token),
            json={
                "course_id": self.course_id,
                "topic_id": self.topic_id,
                "remediation_source": "HUMAN_EXPERT",
            },
        )
        self.assertEqual(ready2.status_code, 200)
        self.assertTrue(ready2.json()["flags"].get("human_expert_path") or ready2.json()["eligible"])

    def test_practice_start_and_mastery_via_reassessment_evidence(self):
        rec = client.post(
            "/mastery/practice/recommend",
            headers=_auth(self.student_token),
            json={"course_id": self.course_id, "topic_id": self.topic_id},
        )
        self.assertEqual(rec.status_code, 200, rec.text)
        self.assertIn("why_selected", rec.json())

        started = client.post(
            "/mastery/practice/start",
            headers=_auth(self.student_token),
            json={"course_id": self.course_id, "topic_id": self.topic_id},
        )
        self.assertEqual(started.status_code, 200, started.text)
        self.assertIn("assessment_id", started.json())
        aid = started.json()["assessment_id"]

        # Simulate high practice accuracy by writing mastery state then checking eligibility
        db = database.SessionLocal()
        try:
            state = (
                db.query(models.TopicMasteryState)
                .filter(
                    models.TopicMasteryState.student_id == self.student_id,
                    models.TopicMasteryState.course_id == self.course_id,
                    models.TopicMasteryState.topic_id == self.topic_id,
                )
                .first()
            )
            self.assertIsNotNone(state)
            state.practice_accuracy = 85.0
            db.commit()
        finally:
            db.close()

        elig = client.get(
            "/mastery/reassessment/eligibility",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id, "topic_id": self.topic_id},
        )
        self.assertEqual(elig.status_code, 200)
        self.assertTrue(elig.json()["eligible"])

        re_start = client.post(
            "/mastery/reassessment/start",
            headers=_auth(self.student_token),
            json={"course_id": self.course_id, "topic_id": self.topic_id},
        )
        self.assertEqual(re_start.status_code, 200, re_start.text)
        re_aid = re_start.json()["assessment_id"]
        self.assertNotEqual(re_aid, aid)

        # Build evaluated attempt + performance records, then run mastery processor
        db = database.SessionLocal()
        try:
            assessment = db.query(models.Assessment).filter(models.Assessment.id == re_aid).first()
            version = (
                db.query(models.AssessmentVersion)
                .filter(models.AssessmentVersion.assessment_id == re_aid)
                .order_by(models.AssessmentVersion.version_number.desc())
                .first()
            )
            aqs = (
                db.query(models.AssessmentQuestion)
                .filter(models.AssessmentQuestion.version_id == version.id)
                .all()
            )
            n = len(aqs)
            correct_n = max(1, int(round(n * 0.9)))
            attempt = models.AssessmentAttempt(
                assessment_id=re_aid,
                version_id=version.id,
                student_id=self.student_id,
                course_id=self.course_id,
                status="EVALUATED",
                total_marks_available=float(n),
                total_marks_obtained=float(correct_n),
                percentage=round(100.0 * correct_n / n, 2) if n else 0.0,
                correct_count=correct_n,
                incorrect_count=n - correct_n,
                unanswered_count=0,
                attempt_number=1,
            )
            db.add(attempt)
            db.flush()
            for i, aq in enumerate(aqs):
                ok = i < correct_n
                db.add(
                    models.PerformanceRecord(
                        attempt_id=attempt.id,
                        student_id=self.student_id,
                        course_id=self.course_id,
                        assessment_id=re_aid,
                        assessment_version_id=version.id,
                        assessment_type="TOPIC_REASSESSMENT",
                        subject_id=self.subject_id,
                        topic_id=self.topic_id,
                        question_id=aq.question_id,
                        marks_available=1.0,
                        marks_obtained=1.0 if ok else 0.0,
                        is_correct=ok,
                        is_incorrect=not ok,
                        is_unanswered=False,
                        attempt_number=1,
                    )
                )
            db.commit()
            db.refresh(attempt)
            # ensure relationship
            attempt.assessment = assessment
            result = process_attempt_for_mastery(db, attempt)
            self.assertTrue(result.get("decision", {}).get("mastered"))
        finally:
            db.close()

        mine = client.get(
            "/mastery/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(mine.status_code, 200, mine.text)
        topics = {t["topic_id"]: t for t in mine.json()["topics"]}
        self.assertEqual(topics[self.topic_id]["status"], "MASTERED")
        self.assertEqual(topics[self.topic_id]["indicator"], "GREEN")

        detail = client.get(
            f"/mastery/students/{self.student_id}/courses/{self.course_id}/topics/{self.topic_id}",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(any(h["event_type"] == "MASTERED" for h in detail.json()["history"]))
        self.assertFalse(
            detail.json()["explanation"].get("remediation_source_affects_decision", True)
            if "remediation_source_affects_decision" in (detail.json().get("explanation") or {})
            else False
        )

    def test_failed_reassessment_keeps_gap(self):
        db = database.SessionLocal()
        try:
            policy = mastery.get_policy(db, self.course_id)
        finally:
            db.close()
        decision = evaluate_mastery_decision(
            percentage=50, questions=8, correct=4, policy=policy
        )
        self.assertEqual(decision["decision"], "GAP_PERSISTS")
        self.assertEqual(decision["explanation"]["next_action"], "ADAPTIVE_PRACTICE_OR_REMEDIATION")

    def test_student_cannot_set_other_student_practice(self):
        denied = client.post(
            "/mastery/practice/start",
            headers=_auth(self.other_token),
            json={
                "course_id": self.course_id,
                "topic_id": self.topic_id,
                "student_id": self.student_id,
            },
        )
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
