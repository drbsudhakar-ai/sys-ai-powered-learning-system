"""P0-010 Question Knowledge Base & Intelligence tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _email(p: str) -> str:
    return f"{p}_{uuid.uuid4().hex[:10]}@example.com"


def _reg(role: str, extra: dict):
    email = _email(role)
    r = client.post(
        "/auth/register",
        json={"name": f"P010 {role}", "email": email, "role": role, "password": "TestPass123!", **extra},
    )
    assert r.status_code == 201, r.text
    l = client.post("/auth/login", data={"username": email, "password": "TestPass123!"})
    assert l.status_code == 200, l.text
    return l.json()["access_token"], r.json()["id"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


class QuestionIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin, cls.admin_id = _reg("admin", {"employee_code": "P010A"})
        cls.coord, cls.coord_id = _reg("faculty", {"employee_code": "P010C"})
        cls.expert, cls.expert_id = _reg("faculty", {"employee_code": "P010E"})
        cls.other, cls.other_id = _reg("faculty", {"employee_code": "P010X"})
        cls.student, cls.student_id = _reg("student", {"roll_number": "P010S"})

        course = client.post("/courses/", headers=H(cls.admin), json={"title": "P010 Course", "description": "q"})
        assert course.status_code == 201, course.text
        cls.course_id = course.json()["id"]

        assert (
            client.post(
                "/admin/course-coordinators",
                headers=H(cls.admin),
                json={"faculty_id": cls.coord_id, "course_id": cls.course_id},
            ).status_code
            == 201
        )

        s1 = client.post(
            "/admin/subjects",
            headers=H(cls.admin),
            json={"name": f"Math-{uuid.uuid4().hex[:5]}", "course_id": cls.course_id},
        )
        s2 = client.post(
            "/admin/subjects",
            headers=H(cls.admin),
            json={"name": f"Phys-{uuid.uuid4().hex[:5]}", "course_id": cls.course_id},
        )
        assert s1.status_code == 201 and s2.status_code == 201
        cls.sub1, cls.sub2 = s1.json()["id"], s2.json()["id"]

        assert (
            client.post(
                "/admin/subject-experts",
                headers=H(cls.admin),
                json={"faculty_id": cls.expert_id, "subject_id": cls.sub1},
            ).status_code
            == 201
        )

        t1 = client.post("/topics", headers=H(cls.admin), json={"name": "Probability", "subject_id": cls.sub1})
        t2 = client.post("/topics", headers=H(cls.admin), json={"name": "Mechanics", "subject_id": cls.sub2})
        assert t1.status_code == 201 and t2.status_code == 201
        cls.topic1, cls.topic2 = t1.json()["id"], t2.json()["id"]

    def test_authz_student_and_unrelated_faculty(self):
        self.assertEqual(client.get("/question-bank/questions").status_code, 401)
        self.assertEqual(
            client.get("/question-bank/questions", headers=H(self.student), params={"course_id": self.course_id}).status_code,
            403,
        )
        created = client.post(
            "/question-bank/questions",
            headers=H(self.other),
            json={
                "stem": "Unauthorized Q",
                "course_id": self.course_id,
                "subject_id": self.sub1,
                "difficulty": "MEDIUM",
            },
        )
        self.assertEqual(created.status_code, 403)

    def test_subject_expert_and_coordinator_can_author(self):
        q1 = client.post(
            "/question-bank/questions",
            headers=H(self.expert),
            json={
                "stem": f"Expert Q {uuid.uuid4().hex[:6]}",
                "course_id": self.course_id,
                "subject_id": self.sub1,
                "topic_id": self.topic1,
                "difficulty": "MEDIUM",
                "status": "ACTIVE",
                "correct_answer": "A",
                "options": ["A", "B", "C", "D"],
                "shortcut": "use formula",
                "common_traps": "sign error",
                "concept_tags": ["probability", "bayes"],
                "quality_score": 0.9,
            },
        )
        self.assertEqual(q1.status_code, 201, q1.text)

        q2 = client.post(
            "/question-bank/questions",
            headers=H(self.coord),
            json={
                "stem": f"Coord Q {uuid.uuid4().hex[:6]}",
                "course_id": self.course_id,
                "subject_id": self.sub2,
                "topic_id": self.topic2,
                "difficulty": "HARD",
                "status": "ACTIVE",
                "correct_answer": "B",
                "options": ["A", "B", "C", "D"],
                "quality_score": 0.85,
            },
        )
        self.assertEqual(q2.status_code, 201, q2.text)

    def test_duplicate_protection(self):
        text = f"Unique duplicate probe {uuid.uuid4().hex}"
        a = client.post(
            "/question-bank/questions",
            headers=H(self.admin),
            json={
                "stem": text,
                "course_id": self.course_id,
                "subject_id": self.sub1,
                "topic_id": self.topic1,
                "status": "ACTIVE",
                "correct_answer": "A",
                "options": ["A", "B"],
            },
        )
        self.assertEqual(a.status_code, 201, a.text)
        b = client.post(
            "/question-bank/questions",
            headers=H(self.admin),
            json={
                "stem": text,
                "course_id": self.course_id,
                "subject_id": self.sub1,
                "topic_id": self.topic1,
                "status": "DRAFT",
            },
        )
        self.assertEqual(b.status_code, 409)

    def test_historical_analysis_priority_and_ai_lecturer(self):
        # Seed historical papers across years
        for year in (2022, 2023, 2024, 2025):
            paper = client.post(
                "/historical-papers",
                headers=H(self.admin),
                json={
                    "exam_name": f"Mock {year}",
                    "exam_year": year,
                    "course_id": self.course_id,
                    "questions": [
                        {
                            "subject_id": self.sub1,
                            "topic_id": self.topic1,
                            "question_text": f"Prob Q {year}",
                            "marks": 4,
                            "difficulty": "MEDIUM",
                            "concept_tags": ["probability"],
                        },
                        {
                            "subject_id": self.sub2,
                            "topic_id": self.topic2,
                            "question_text": f"Mech Q {year}",
                            "marks": 2 if year < 2024 else 3,
                            "difficulty": "HARD",
                            "concept_tags": ["newton"],
                        },
                    ],
                },
            )
            self.assertEqual(paper.status_code, 201, paper.text)

        analysis = client.post(f"/historical-analysis/{self.course_id}", headers=H(self.admin))
        self.assertEqual(analysis.status_code, 200, analysis.text)
        body = analysis.json()
        self.assertGreaterEqual(body["analysis"]["papers_analyzed"], 4)
        self.assertTrue(len(body["topic_priorities"]) >= 1)
        labels = {p["priority_label"] for p in body["topic_priorities"]}
        self.assertTrue(labels & {"VERY_HIGH", "HIGH", "MEDIUM", "LOW"})

        # weightages
        w = client.put(
            "/weightages/subjects",
            headers=H(self.admin),
            json={
                "course_id": self.course_id,
                "items": [
                    {"subject_id": self.sub1, "weight_percent": 60},
                    {"subject_id": self.sub2, "weight_percent": 40},
                ],
            },
        )
        self.assertEqual(w.status_code, 200, w.text)

        tw = client.put(
            "/weightages/topics",
            headers=H(self.admin),
            json={
                "subject_id": self.sub1,
                "items": [{"topic_id": self.topic1, "weight_percent": 100, "syllabus_importance": 0.9}],
            },
        )
        self.assertEqual(tw.status_code, 200, tw.text)

        intel = client.get(f"/academic-intelligence/topics/{self.topic1}", headers=H(self.admin))
        self.assertEqual(intel.status_code, 200, intel.text)
        self.assertIn("disclaimer", intel.json())
        self.assertIn("priority", intel.json())
        self.assertIn("frequently_tested_concepts", intel.json())

    def test_evidence_selection_and_grand_assessment_integration(self):
        # Ensure enough ACTIVE questions
        for i in range(4):
            client.post(
                "/question-bank/questions",
                headers=H(self.admin),
                json={
                    "stem": f"Select pool Math {i} {uuid.uuid4().hex[:4]}",
                    "course_id": self.course_id,
                    "subject_id": self.sub1,
                    "topic_id": self.topic1,
                    "difficulty": "MEDIUM",
                    "status": "ACTIVE",
                    "correct_answer": "A",
                    "options": ["A", "B", "C", "D"],
                    "quality_score": 0.7 + i * 0.05,
                    "concept_tags": ["probability"],
                },
            )
            client.post(
                "/question-bank/questions",
                headers=H(self.admin),
                json={
                    "stem": f"Select pool Phys {i} {uuid.uuid4().hex[:4]}",
                    "course_id": self.course_id,
                    "subject_id": self.sub2,
                    "topic_id": self.topic2,
                    "difficulty": "MEDIUM",
                    "status": "ACTIVE",
                    "correct_answer": "B",
                    "options": ["A", "B", "C", "D"],
                    "quality_score": 0.75,
                },
            )

        client.post(f"/historical-analysis/{self.course_id}", headers=H(self.admin))

        sel = client.post(
            "/question-selection",
            headers=H(self.admin),
            json={
                "course_id": self.course_id,
                "total_questions": 4,
                "subject_distribution": {self.sub1: 2, self.sub2: 2},
                "difficulty_distribution": {"MEDIUM": 4},
                "reuse_policy": "MIXED",
                "evidence_based": True,
            },
        )
        self.assertEqual(sel.status_code, 200, sel.text)
        data = sel.json()
        self.assertIn("disclaimer", data)
        self.assertGreaterEqual(len(data["selected"]), 1)
        self.assertTrue(all(s.get("evidence_label") == "historically_high_priority" for s in data["selected"]))

        # Grand assessment uses intelligence assemble path
        created = client.post(
            "/assessments/",
            headers=H(self.admin),
            json={
                "title": "Grand Evidence Paper",
                "course_id": self.course_id,
                "assessment_type": "GRAND_TEST",
                "duration_minutes": 180,
                "total_questions": 2,
                "total_marks": 8,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        aid = created.json()["id"]
        bp = client.put(
            f"/assessments/{aid}/blueprint",
            headers=H(self.admin),
            json=[
                {
                    "subject_id": self.sub1,
                    "topic_id": self.topic1,
                    "difficulty": "MEDIUM",
                    "question_count": 1,
                },
                {
                    "subject_id": self.sub2,
                    "topic_id": self.topic2,
                    "difficulty": "MEDIUM",
                    "question_count": 1,
                },
            ],
        )
        self.assertEqual(bp.status_code, 200, bp.text)
        pub = client.post(f"/assessments/{aid}/publish", headers=H(self.admin))
        self.assertEqual(pub.status_code, 200, pub.text)
        self.assertEqual(pub.json()["question_count"], 2)

    def test_lifecycle_duplicate_archive(self):
        created = client.post(
            "/question-bank/questions",
            headers=H(self.admin),
            json={
                "stem": f"Lifecycle {uuid.uuid4().hex}",
                "course_id": self.course_id,
                "subject_id": self.sub1,
                "status": "DRAFT",
                "options": ["A", "B"],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        qid = created.json()["id"]
        dup = client.post(f"/question-bank/questions/{qid}/duplicate", headers=H(self.admin))
        self.assertEqual(dup.status_code, 201)
        arch = client.post(f"/question-bank/questions/{qid}/archive", headers=H(self.admin))
        self.assertEqual(arch.status_code, 200)
        self.assertEqual(arch.json()["status"], "ARCHIVED")


if __name__ == "__main__":
    unittest.main()
