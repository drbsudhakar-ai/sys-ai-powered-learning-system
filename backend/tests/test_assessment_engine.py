"""
P0-009 Assessment Engine, reporting, and notification tests.
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

client = TestClient(app)
_users = ProtectedUserFactory(client, "P009")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class AssessmentEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P009A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P009F"})
        cls.other_faculty_token, cls.other_faculty_id = _register_login(
            "faculty", {"employee_code": "P009F2"}
        )
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P009S"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P009 Course", "description": "assessment course"},
        )
        assert course.status_code == 201, course.text
        cls.course_id = course.json()["id"]

        # Assign coordinator
        assign = client.post(
            "/admin/course-coordinators",
            headers=_auth(cls.admin_token),
            json={"faculty_id": cls.faculty_id, "course_id": cls.course_id},
        )
        assert assign.status_code == 201, assign.text

        sub = client.post(
            "/admin/subjects",
            headers=_auth(cls.admin_token),
            json={"name": f"Math-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201, sub.text
        cls.subject_id = sub.json()["id"]

        sub2 = client.post(
            "/admin/subjects",
            headers=_auth(cls.admin_token),
            json={"name": f"Phys-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub2.status_code == 201, sub2.text
        cls.subject2_id = sub2.json()["id"]

        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Algebra", "subject_id": cls.subject_id},
        )
        assert topic.status_code == 201, topic.text
        cls.topic_id = topic.json()["id"]

        topic2 = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Mechanics", "subject_id": cls.subject2_id},
        )
        assert topic2.status_code == 201, topic2.text
        cls.topic2_id = topic2.json()["id"]

    def test_unauthenticated_and_student_cannot_manage(self):
        self.assertEqual(client.get("/assessments/").status_code, 401)
        created = client.post(
            "/assessments/",
            headers=_auth(self.student_token),
            json={
                "title": "Nope",
                "course_id": self.course_id,
                "assessment_type": "WEEKLY_TEST",
                "duration_minutes": 60,
                "total_questions": 10,
                "total_marks": 40,
            },
        )
        self.assertEqual(created.status_code, 403)

    def test_non_coordinator_faculty_rejected(self):
        created = client.post(
            "/assessments/",
            headers=_auth(self.other_faculty_token),
            json={
                "title": "Nope",
                "course_id": self.course_id,
                "assessment_type": "WEEKLY_TEST",
                "duration_minutes": 60,
                "total_questions": 10,
                "total_marks": 40,
            },
        )
        self.assertEqual(created.status_code, 403)

    def test_topic_test_blueprint_assemble_publish(self):
        created = client.post(
            "/assessments/",
            headers=_auth(self.faculty_token),
            json={
                "title": "Algebra Topic Test",
                "course_id": self.course_id,
                "assessment_type": "TOPIC_TEST",
                "duration_minutes": 30,
                "total_questions": 3,
                "total_marks": 12,
                "marks_correct": 4,
                "marks_incorrect": -1,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        aid = created.json()["id"]
        self.assertEqual(created.json()["category"], "TOPIC_MASTERY")
        self.assertEqual(created.json()["status"], "DRAFT")

        # Seed questions
        for i in range(3):
            q = client.post(
                "/questions",
                headers=_auth(self.admin_token),
                json={
                    "stem": f"Topic Q{i}",
                    "difficulty": "MEDIUM",
                    "course_id": self.course_id,
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                },
            )
            self.assertEqual(q.status_code, 201, q.text)

        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=_auth(self.faculty_token),
            json=[
                {
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                    "difficulty": "MEDIUM",
                    "question_count": 3,
                }
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)

        assembled = client.post(f"/assessments/{aid}/assemble", headers=_auth(self.faculty_token))
        self.assertEqual(assembled.status_code, 200)
        self.assertTrue(assembled.json()["ok"])

        published = client.post(f"/assessments/{aid}/publish", headers=_auth(self.faculty_token))
        self.assertEqual(published.status_code, 200, published.text)
        self.assertEqual(published.json()["question_count"], 3)

        detail = client.get(f"/assessments/{aid}", headers=_auth(self.admin_token))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "PUBLISHED")
        self.assertEqual(len(detail.json()["versions"]), 1)
        self.assertEqual(len(detail.json()["versions"][0]["questions"]), 3)

    def test_weekly_multi_subject_and_insufficient_questions(self):
        created = client.post(
            "/assessments/",
            headers=_auth(self.admin_token),
            json={
                "title": "Weekly 01",
                "course_id": self.course_id,
                "assessment_type": "WEEKLY_TEST",
                "duration_minutes": 60,
                "total_questions": 4,
                "total_marks": 16,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["category"], "PERIODIC_EVALUATION")
        aid = created.json()["id"]

        for difficulty, subject, topic, n in [
            ("EASY", self.subject_id, self.topic_id, 2),
            ("MEDIUM", self.subject2_id, self.topic2_id, 1),  # insufficient for need=2
        ]:
            for i in range(n):
                client.post(
                    "/questions",
                    headers=_auth(self.admin_token),
                    json={
                        "stem": f"W {difficulty} {i}",
                        "difficulty": difficulty,
                        "course_id": self.course_id,
                        "subject_id": subject,
                        "topic_id": topic,
                    },
                )

        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=_auth(self.admin_token),
            json=[
                {
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                    "difficulty": "EASY",
                    "question_count": 2,
                },
                {
                    "subject_id": self.subject2_id,
                    "topic_id": self.topic2_id,
                    "difficulty": "MEDIUM",
                    "question_count": 2,
                },
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)

        pub = client.post(f"/assessments/{aid}/publish", headers=_auth(self.admin_token))
        self.assertEqual(pub.status_code, 422)

        # Add missing question and publish
        client.post(
            "/questions",
            headers=_auth(self.admin_token),
            json={
                "stem": "W MEDIUM extra",
                "difficulty": "MEDIUM",
                "course_id": self.course_id,
                "subject_id": self.subject2_id,
                "topic_id": self.topic2_id,
            },
        )
        pub2 = client.post(f"/assessments/{aid}/publish", headers=_auth(self.admin_token))
        self.assertEqual(pub2.status_code, 200, pub2.text)

    def test_grand_and_final_types(self):
        for a_type, category in [
            ("MONTHLY_TEST", "PERIODIC_EVALUATION"),
            ("GRAND_TEST", "CUMULATIVE_EVALUATION"),
            ("FINAL_GRAND_TEST", "FINAL_READINESS"),
        ]:
            res = client.post(
                "/assessments/",
                headers=_auth(self.admin_token),
                json={
                    "title": f"{a_type} sample",
                    "course_id": self.course_id,
                    "assessment_type": a_type,
                    "duration_minutes": 120,
                    "total_questions": 2,
                    "total_marks": 8,
                },
            )
            self.assertEqual(res.status_code, 201, res.text)
            self.assertEqual(res.json()["category"], category)

    def test_performance_sheet_report_pdf_and_authz(self):
        # Create + publish a dedicated assessment for result fixtures
        created = client.post(
            "/assessments/",
            headers=_auth(self.admin_token),
            json={
                "title": "Perf Fixture Test",
                "course_id": self.course_id,
                "assessment_type": "TOPIC_TEST",
                "duration_minutes": 20,
                "total_questions": 1,
                "total_marks": 4,
                "marks_correct": 4,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        aid = created.json()["id"]
        q = client.post(
            "/questions",
            headers=_auth(self.admin_token),
            json={
                "stem": "Perf Q1",
                "difficulty": "EASY",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
            },
        )
        self.assertEqual(q.status_code, 201, q.text)
        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=_auth(self.admin_token),
            json=[
                {
                    "subject_id": self.subject_id,
                    "topic_id": self.topic_id,
                    "difficulty": "EASY",
                    "question_count": 1,
                }
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)
        pub = client.post(f"/assessments/{aid}/publish", headers=_auth(self.admin_token))
        self.assertEqual(pub.status_code, 200, pub.text)

        db = database.SessionLocal()
        try:
            assessment = db.query(models.Assessment).filter(models.Assessment.id == aid).first()
            self.assertIsNotNone(assessment)
            version = (
                db.query(models.AssessmentVersion)
                .filter(models.AssessmentVersion.assessment_id == assessment.id)
                .first()
            )
            self.assertIsNotNone(version)
            attempt = models.AssessmentAttempt(
                student_id=self.student_id,
                assessment_id=assessment.id,
                version_id=version.id,
                course_id=self.course_id,
                attempt_number=1,
                status="EVALUATED",
                total_marks_obtained=8,
                total_marks_available=12,
                percentage=66.67,
            )
            db.add(attempt)
            db.flush()
            aq = (
                db.query(models.AssessmentQuestion)
                .filter(models.AssessmentQuestion.version_id == version.id)
                .first()
            )
            db.add(
                models.PerformanceRecord(
                    attempt_id=attempt.id,
                    student_id=self.student_id,
                    course_id=self.course_id,
                    assessment_id=assessment.id,
                    assessment_version_id=version.id,
                    assessment_category=assessment.category,
                    assessment_type=assessment.assessment_type,
                    assessment_date=attempt.submitted_at,
                    subject_id=aq.subject_id if aq else self.subject_id,
                    topic_id=aq.topic_id if aq else self.topic_id,
                    question_id=aq.question_id if aq else q.json()["id"],
                    difficulty=aq.difficulty if aq else "EASY",
                    marks_available=4,
                    marks_obtained=4,
                    is_correct=True,
                    is_incorrect=False,
                    is_unanswered=False,
                    response_time_seconds=30,
                    negative_marks=0,
                    attempt_number=1,
                )
            )
            db.commit()
        finally:
            db.close()

        sheet = client.get(
            "/performance/sheet",
            headers=_auth(self.admin_token),
            params={"student_id": self.student_id, "course_id": self.course_id},
        )
        self.assertEqual(sheet.status_code, 200, sheet.text)
        body = sheet.json()
        self.assertEqual(body["student"]["id"], self.student_id)
        self.assertGreaterEqual(body["overall_summary"]["total_assessments"], 1)

        # student cannot access
        self.assertEqual(
            client.get(
                "/performance/sheet",
                headers=_auth(self.student_token),
                params={"student_id": self.student_id, "course_id": self.course_id},
            ).status_code,
            403,
        )
        # other faculty cannot
        self.assertEqual(
            client.get(
                "/performance/sheet",
                headers=_auth(self.other_faculty_token),
                params={"student_id": self.student_id, "course_id": self.course_id},
            ).status_code,
            403,
        )

        card = client.get(
            "/performance/report-card",
            headers=_auth(self.faculty_token),
            params={"student_id": self.student_id, "course_id": self.course_id},
        )
        self.assertEqual(card.status_code, 200, card.text)

        pdf = client.get(
            "/performance/report-card.pdf",
            headers=_auth(self.admin_token),
            params={"student_id": self.student_id, "course_id": self.course_id},
        )
        self.assertEqual(pdf.status_code, 200, pdf.text)
        self.assertTrue(pdf.headers["content-type"].startswith("application/pdf"))
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_notifications_config_and_retry(self):
        created = client.post(
            "/notifications/recipients",
            headers=_auth(self.admin_token),
            json={
                "name": "Academic Director",
                "designation": "Director",
                "email": _email("director"),
                "recipient_type": "HIGHER_OFFICIAL",
                "event_types": ["ASSESSMENT_PUBLISHED", "REPORT_CARD_GENERATED"],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)

        # student cannot configure
        self.assertEqual(
            client.get("/notifications/recipients", headers=_auth(self.student_token)).status_code,
            403,
        )

        notes = client.get("/notifications", headers=_auth(self.admin_token))
        self.assertEqual(notes.status_code, 200)
        # Publish creates a notification that fails soft without SMTP
        if notes.json():
            nid = notes.json()[0]["id"]
            retried = client.post(f"/notifications/{nid}/retry", headers=_auth(self.admin_token))
            self.assertEqual(retried.status_code, 200)
            self.assertIn(retried.json()["status"], ("FAILED", "SENT", "RETRYING", "PENDING", "PARTIAL", "PROCESSING"))


if __name__ == "__main__":
    unittest.main()
