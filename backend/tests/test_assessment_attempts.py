"""
P0-011 Student assessment attempt, evaluation, and answer-key tests.
Uses live DB-backed TestClient flows (not fixture-only evaluation).
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from tests.auth_helpers import ProtectedUserFactory
from app.main import app
from app import models, database

client = TestClient(app)
_users = ProtectedUserFactory(client, "P011")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class AssessmentAttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P011A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P011F"})
        cls.expert_token, cls.expert_id = _register_login("faculty", {"employee_code": "P011E"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P011S"})
        cls.other_student_token, cls.other_student_id = _register_login(
            "student", {"roll_number": "P011S2"}
        )

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P011 Course", "description": "attempt course"},
        )
        assert course.status_code == 201, course.text
        cls.course_id = course.json()["id"]

        assign = client.post(
            "/admin/course-coordinators",
            headers=_auth(cls.admin_token),
            json={"faculty_id": cls.faculty_id, "course_id": cls.course_id},
        )
        assert assign.status_code == 201, assign.text

        sub = client.post(
            "/admin/subjects",
            headers=_auth(cls.admin_token),
            json={"name": f"Calc-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201, sub.text
        cls.subject_id = sub.json()["id"]

        sub2 = client.post(
            "/admin/subjects",
            headers=_auth(cls.admin_token),
            json={"name": f"Alg-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub2.status_code == 201, sub2.text
        cls.subject2_id = sub2.json()["id"]

        expert = client.post(
            "/admin/subject-experts",
            headers=_auth(cls.admin_token),
            json={"faculty_id": cls.expert_id, "subject_id": cls.subject_id},
        )
        assert expert.status_code == 201, expert.text

        t1 = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Derivatives", "subject_id": cls.subject_id},
        )
        assert t1.status_code == 201, t1.text
        cls.topic_id = t1.json()["id"]

        t2 = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Equations", "subject_id": cls.subject2_id},
        )
        assert t2.status_code == 201, t2.text
        cls.topic2_id = t2.json()["id"]

        # Enroll primary student
        en = client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student_token))
        assert en.status_code == 201, en.text

    def _seed_question(self, *, stem, subject_id, topic_id, difficulty, options, correct, explanation="Because"):
        q = client.post(
            "/question-bank/questions",
            headers=_auth(self.admin_token),
            json={
                "stem": stem,
                "question_type": "SINGLE_MCQ",
                "difficulty": difficulty,
                "status": "ACTIVE",
                "course_id": self.course_id,
                "subject_id": subject_id,
                "topic_id": topic_id,
                "options": options,
                "correct_answer": correct,
                "explanation": explanation,
                "shortcut": "Use identity",
                "alternative_solution": "Graphically",
                "marks": 2.0,
                "negative_marks": -0.5,
            },
        )
        self.assertEqual(q.status_code, 201, q.text)
        return q.json()

    def _publish_assessment(self, *, title="P011 Live Test", duration=30, max_attempts=1, questions=None):
        created = client.post(
            "/assessments/",
            headers=_auth(self.faculty_token),
            json={
                "title": title,
                "course_id": self.course_id,
                "assessment_type": "WEEKLY_TEST",
                "duration_minutes": duration,
                "total_questions": 3,
                "total_marks": 6,
                "marks_correct": 2,
                "marks_incorrect": -0.5,
                "marks_unanswered": 0,
                "max_attempts": max_attempts,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        aid = created.json()["id"]

        if questions is None:
            questions = [
                self._seed_question(
                    stem=f"{title} Q1 {uuid.uuid4().hex[:4]}",
                    subject_id=self.subject_id,
                    topic_id=self.topic_id,
                    difficulty="EASY",
                    options=["A", "B", "C", "D"],
                    correct="A",
                ),
                self._seed_question(
                    stem=f"{title} Q2 {uuid.uuid4().hex[:4]}",
                    subject_id=self.subject_id,
                    topic_id=self.topic_id,
                    difficulty="MEDIUM",
                    options=["A", "B", "C", "D"],
                    correct="B",
                ),
                self._seed_question(
                    stem=f"{title} Q3 {uuid.uuid4().hex[:4]}",
                    subject_id=self.subject2_id,
                    topic_id=self.topic2_id,
                    difficulty="HARD",
                    options=["A", "B", "C", "D"],
                    correct="C",
                ),
            ]

        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=_auth(self.faculty_token),
            json=[
                {
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                    "difficulty": "EASY",
                    "question_count": 1,
                },
                {
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                    "difficulty": "MEDIUM",
                    "question_count": 1,
                },
                {
                    "subject_id": self.subject2_id,
                    "topic_id": self.topic2_id,
                    "difficulty": "HARD",
                    "question_count": 1,
                },
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)
        pub = client.post(f"/assessments/{aid}/publish", headers=_auth(self.faculty_token))
        self.assertEqual(pub.status_code, 200, pub.text)
        return aid, pub.json()["version_id"], questions

    def test_unauthenticated_blocked(self):
        self.assertEqual(client.get("/student/assessments").status_code, 401)
        self.assertEqual(client.post("/student/assessments/1/start").status_code, 401)
        self.assertEqual(client.get("/assessments/1/answer-key").status_code, 401)

    def test_faculty_cannot_start_attempt(self):
        aid, _, _ = self._publish_assessment(title=f"FacBlock {uuid.uuid4().hex[:6]}")
        start = client.post(
            f"/student/assessments/{aid}/start", headers=_auth(self.faculty_token)
        )
        self.assertEqual(start.status_code, 403)

    def test_unenrolled_student_cannot_start(self):
        aid, _, _ = self._publish_assessment(title=f"Unenroll {uuid.uuid4().hex[:6]}")
        start = client.post(
            f"/student/assessments/{aid}/start", headers=_auth(self.other_student_token)
        )
        self.assertEqual(start.status_code, 403)

    def test_full_lifecycle_save_resume_submit_eval_answer_key(self):
        aid, version_id, _ = self._publish_assessment(title=f"Life {uuid.uuid4().hex[:6]}")

        # Answer key blocked while active / not released
        ak_early = client.get(f"/assessments/{aid}/answer-key", headers=_auth(self.student_token))
        self.assertEqual(ak_early.status_code, 403)

        start = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(start.status_code, 201, start.text)
        attempt_id = start.json()["attempt_id"]
        self.assertEqual(start.json()["status"], "IN_PROGRESS")
        self.assertGreater(start.json()["remaining_seconds"], 0)

        # Resume returns same attempt
        start2 = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(start2.status_code, 201)
        self.assertEqual(start2.json()["attempt_id"], attempt_id)

        get1 = client.get(f"/student/attempts/{attempt_id}", headers=_auth(self.student_token))
        self.assertEqual(get1.status_code, 200, get1.text)
        questions = get1.json()["questions"]
        self.assertEqual(len(questions), 3)
        # Live attempt must not leak correct answers
        self.assertNotIn("correct_answer", questions[0])

        # Resolve expected answers from immutable snapshots (server truth)
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

        q_correct = next(q for q in questions if snaps[q["assessment_question_id"]].correct_answer_snapshot)
        q_wrong = next(
            q
            for q in questions
            if q["assessment_question_id"] != q_correct["assessment_question_id"]
        )
        q_blank = next(
            q
            for q in questions
            if q["assessment_question_id"]
            not in (q_correct["assessment_question_id"], q_wrong["assessment_question_id"])
        )
        correct_ans = snaps[q_correct["assessment_question_id"]].correct_answer_snapshot
        opts = snaps[q_wrong["assessment_question_id"]].options_snapshot or ["A", "B", "C", "D"]
        wrong_ans = next(
            o for o in opts if o != snaps[q_wrong["assessment_question_id"]].correct_answer_snapshot
        )

        s1 = client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=_auth(self.student_token),
            json={
                "assessment_question_id": q_correct["assessment_question_id"],
                "selected_answer": correct_ans,
                "time_spent_delta": 12,
            },
        )
        self.assertEqual(s1.status_code, 200, s1.text)

        s2 = client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=_auth(self.student_token),
            json={
                "assessment_question_id": q_wrong["assessment_question_id"],
                "selected_answer": wrong_ans,
                "marked_for_review": True,
                "time_spent_delta": 8,
            },
        )
        self.assertEqual(s2.status_code, 200, s2.text)

        s3 = client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=_auth(self.student_token),
            json={
                "assessment_question_id": q_blank["assessment_question_id"],
                "selected_answer": "C",
                "time_spent_delta": 5,
            },
        )
        self.assertEqual(s3.status_code, 200)
        clear = client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=_auth(self.student_token),
            json={"assessment_question_id": q_blank["assessment_question_id"], "clear": True},
        )
        self.assertEqual(clear.status_code, 200)
        self.assertFalse(clear.json()["response"]["answered"])

        # Other student cannot access
        other = client.get(f"/student/attempts/{attempt_id}", headers=_auth(self.other_student_token))
        self.assertEqual(other.status_code, 403)

        # Client-supplied score must be ignored (no score field accepted on submit)
        submit = client.post(
            f"/student/attempts/{attempt_id}/submit",
            headers=_auth(self.student_token),
            json={"score": 999, "percentage": 100},
        )
        self.assertEqual(submit.status_code, 200, submit.text)
        result = submit.json()
        self.assertEqual(result["status"], "EVALUATED")
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["incorrect"], 1)
        self.assertEqual(result["unanswered"], 1)
        # marks from question.marks=2.0 / negative -0.5
        self.assertAlmostEqual(result["score"], 1.5, places=2)
        self.assertNotEqual(result["score"], 999)

        # Immutable after submit
        save_after = client.post(
            f"/student/attempts/{attempt_id}/responses",
            headers=_auth(self.student_token),
            json={
                "assessment_question_id": q_correct["assessment_question_id"],
                "selected_answer": "B",
            },
        )
        self.assertEqual(save_after.status_code, 400)

        # Performance Analyzer contract rows
        db = database.SessionLocal()
        try:
            rows = (
                db.query(models.PerformanceRecord)
                .filter(models.PerformanceRecord.attempt_id == attempt_id)
                .all()
            )
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r.assessment_version_id == version_id for r in rows))
            self.assertTrue(any(r.is_correct for r in rows))
            self.assertTrue(any(r.is_incorrect for r in rows))
            self.assertTrue(any(r.is_unanswered for r in rows))
            subjects = {r.subject_id for r in rows if r.subject_id}
            topics = {r.topic_id for r in rows if r.topic_id}
            diffs = {r.difficulty for r in rows if r.difficulty}
            self.assertGreaterEqual(len(subjects), 2)
            self.assertGreaterEqual(len(topics), 2)
            self.assertGreaterEqual(len(diffs), 2)
        finally:
            db.close()

        # Subject/topic/difficulty in result
        self.assertTrue(result["subject_performance"])
        self.assertTrue(result["topic_performance"])
        self.assertTrue(result["difficulty_performance"])

        # Answer key still blocked until release while window open
        ak2 = client.get(f"/assessments/{aid}/answer-key", headers=_auth(self.student_token))
        self.assertEqual(ak2.status_code, 403)

        release = client.post(
            f"/assessments/{aid}/release-answer-key", headers=_auth(self.faculty_token)
        )
        self.assertEqual(release.status_code, 200, release.text)

        # Universal access
        for token in (self.student_token, self.faculty_token, self.expert_token, self.admin_token):
            ak = client.get(f"/assessments/{aid}/answer-key", headers=_auth(token))
            self.assertEqual(ak.status_code, 200, ak.text)
            body = ak.json()
            self.assertEqual(len(body["questions"]), 3)
            self.assertTrue(body["questions"][0]["correct_answer"])
            self.assertTrue(body["questions"][0]["explanation"])
            pdf = client.get(f"/assessments/{aid}/answer-key.pdf", headers=_auth(token))
            self.assertEqual(pdf.status_code, 200, pdf.text)
            self.assertEqual(pdf.headers.get("content-type"), "application/pdf")
            self.assertTrue(pdf.content.startswith(b"%PDF"))
            self.assertIn(b"SYS", pdf.content)
            self.assertGreater(len(pdf.content), 400)

        # Historical immutability: edit bank question, snapshot unchanged
        db = database.SessionLocal()
        try:
            aq = (
                db.query(models.AssessmentQuestion)
                .filter(models.AssessmentQuestion.version_id == version_id)
                .order_by(models.AssessmentQuestion.sequence)
                .first()
            )
            original_correct = aq.correct_answer_snapshot
            bank_q = db.query(models.Question).filter(models.Question.id == aq.question_id).first()
            bank_q.correct_answer = "ZZZ_CHANGED"
            bank_q.stem = "CHANGED STEM"
            db.commit()
            aq_id = aq.id
        finally:
            db.close()

        ak3 = client.get(f"/assessments/{aid}/answer-key", headers=_auth(self.student_token))
        self.assertEqual(ak3.status_code, 200)
        snap_q = next(
            q for q in ak3.json()["questions"] if q["sequence"] == 1
        )
        self.assertEqual(snap_q["correct_answer"], original_correct)
        self.assertNotEqual(snap_q["stem"], "CHANGED STEM")

        # Attempt remains tied to version
        res2 = client.get(f"/student/attempts/{attempt_id}/result", headers=_auth(self.student_token))
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["version_id"], version_id)

        # Attempt limit
        again = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(again.status_code, 403)

    def test_availability_window_and_auto_submit(self):
        aid, _, _ = self._publish_assessment(
            title=f"Timer {uuid.uuid4().hex[:6]}", duration=1, max_attempts=2
        )
        # Force future window
        db = database.SessionLocal()
        try:
            a = db.query(models.Assessment).filter(models.Assessment.id == aid).first()
            a.available_from = datetime.now(timezone.utc) + timedelta(days=1)
            db.commit()
        finally:
            db.close()
        blocked = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(blocked.status_code, 403)

        db = database.SessionLocal()
        try:
            a = db.query(models.Assessment).filter(models.Assessment.id == aid).first()
            a.available_from = datetime.now(timezone.utc) - timedelta(hours=1)
            a.available_until = None
            db.commit()
        finally:
            db.close()

        start = client.post(f"/student/assessments/{aid}/start", headers=_auth(self.student_token))
        self.assertEqual(start.status_code, 201, start.text)
        attempt_id = start.json()["attempt_id"]

        # Expire attempt server-side
        db = database.SessionLocal()
        try:
            at = db.query(models.AssessmentAttempt).filter(models.AssessmentAttempt.id == attempt_id).first()
            at.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
            db.commit()
        finally:
            db.close()

        get_expired = client.get(f"/student/attempts/{attempt_id}", headers=_auth(self.student_token))
        self.assertEqual(get_expired.status_code, 200)
        self.assertIn(get_expired.json()["status"], ("EVALUATED", "AUTO_SUBMITTED", "SUBMITTED"))

        result = client.get(f"/student/attempts/{attempt_id}/result", headers=_auth(self.student_token))
        self.assertEqual(result.status_code, 200)
        # Auto-submit should mark auto_submitted
        db = database.SessionLocal()
        try:
            at = db.query(models.AssessmentAttempt).filter(models.AssessmentAttempt.id == attempt_id).first()
            self.assertTrue(at.auto_submitted)
            self.assertEqual(at.status, "EVALUATED")
            assessment = db.query(models.Assessment).filter(models.Assessment.id == aid).first()
            assessment.available_from = None
            db.commit()
        finally:
            db.close()

    def test_student_list_and_instructions(self):
        aid, _, _ = self._publish_assessment(title=f"List {uuid.uuid4().hex[:6]}")
        listing = client.get("/student/assessments", headers=_auth(self.student_token))
        self.assertEqual(listing.status_code, 200)
        data = listing.json()
        self.assertIn("available", data)
        ids = [x["assessment_id"] for x in data["available"] + data["in_progress"] + data["completed"]]
        self.assertIn(aid, ids)

        instr = client.get(
            f"/student/assessments/{aid}/instructions", headers=_auth(self.student_token)
        )
        self.assertEqual(instr.status_code, 200)
        self.assertTrue(instr.json()["available"])


if __name__ == "__main__":
    unittest.main()
