"""
P0-014 Remedial Learning & Group Formation tests.
Uses persisted P0-012 LearningGap rows + P0-013 sessions.
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
_users = ProtectedUserFactory(client, "P014")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_gap(*, student_id, course_id, topic_id, name, classification, high=True):
    db = database.SessionLocal()
    try:
        g = models.LearningGap(
            student_id=student_id,
            course_id=course_id,
            scope_type="TOPIC",
            scope_id=topic_id,
            scope_name=name,
            classification=classification,
            confidence=0.8,
            priority_score=0.7,
            evidence={"kind": "OBSERVED_EVIDENCE", "accuracy": 0.3, "repeated_error_questions": 2},
            inference={"label": "SYSTEM_INFERENCE"},
            is_high_priority=high,
        )
        db.add(g)
        db.commit()
        db.refresh(g)
        return g.id
    finally:
        db.close()


class RemedialLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P014A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P014F"})
        cls.other_faculty_token, cls.other_faculty_id = _register_login(
            "faculty", {"employee_code": "P014F2"}
        )
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P014S1"})
        cls.student2_token, cls.student2_id = _register_login("student", {"roll_number": "P014S2"})
        cls.student3_token, cls.student3_id = _register_login("student", {"roll_number": "P014S3"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P014 Course", "description": "remedial"},
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
            json={"name": "Binary Tree Traversal", "subject_id": cls.subject_id},
        )
        assert topic.status_code == 201
        cls.topic_id = topic.json()["id"]
        topic2 = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "Unique Stack Ops", "subject_id": cls.subject_id},
        )
        assert topic2.status_code == 201
        cls.topic2_id = topic2.json()["id"]

        for tok in (cls.student_token, cls.student2_token, cls.student3_token):
            assert client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(tok)).status_code == 201

        # Shared gap for S1+S2; unique gap for S3
        cls.gap1 = _add_gap(
            student_id=cls.student_id,
            course_id=cls.course_id,
            topic_id=cls.topic_id,
            name="Binary Tree Traversal",
            classification="WEAK",
        )
        cls.gap2 = _add_gap(
            student_id=cls.student2_id,
            course_id=cls.course_id,
            topic_id=cls.topic_id,
            name="Binary Tree Traversal",
            classification="WEAK",
        )
        cls.gap3 = _add_gap(
            student_id=cls.student3_id,
            course_id=cls.course_id,
            topic_id=cls.topic2_id,
            name="Unique Stack Ops",
            classification="CRITICAL_GAP",
        )

    def test_unauthenticated_denied(self):
        self.assertEqual(client.get(f"/remedial/courses/{self.course_id}/gaps").status_code, 401)

    def test_propose_common_and_individual_with_rationale(self):
        denied = client.post(
            f"/remedial/courses/{self.course_id}/proposals",
            headers=_auth(self.other_faculty_token),
        )
        self.assertEqual(denied.status_code, 403)

        prop = client.post(
            f"/remedial/courses/{self.course_id}/proposals",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(prop.status_code, 200, prop.text)
        body = prop.json()
        self.assertTrue(body["common_groups"])
        g = body["common_groups"][0]
        self.assertEqual(g["kind"], "COMMON")
        self.assertGreaterEqual(len(g["members"]), 2)
        self.assertIn("why_grouped", g["explanation"])
        self.assertIn("Binary Tree Traversal", g["explanation"]["summary"])
        self.assertTrue(any(c["kind"] == "INDIVIDUAL" for c in body["individual_candidates"]))

        # Persist created group
        groups = client.get(
            "/remedial/groups",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id, "status": "PROPOSED"},
        )
        self.assertEqual(groups.status_code, 200)
        self.assertTrue(groups.json())

    def test_activate_group_creates_common_session_and_notifies(self):
        prop = client.post(
            f"/remedial/courses/{self.course_id}/proposals",
            headers=_auth(self.faculty_token),
        )
        group_id = prop.json()["common_groups"][0]["id"]
        act = client.post(
            f"/remedial/groups/{group_id}/activate",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(act.status_code, 200, act.text)
        data = act.json()
        self.assertEqual(data["status"], "ACTIVATED")
        self.assertIsNotNone(data["learning_session_id"])
        self.assertIsNotNone(data["intervention"])
        self.assertEqual(data["intervention"]["mode"], "COMMON")
        self.assertTrue(data["intervention"]["reassessment_required"])

        # Students can open lecture on linked session
        sid = data["learning_session_id"]
        lec = client.post(
            f"/learning-sessions/{sid}/lecture/open",
            headers=_auth(self.student_token),
        )
        self.assertEqual(lec.status_code, 200, lec.text)
        self.assertIn("teaching_plan", lec.json())

        # Peer privacy: student view of group has no other students' evidence
        gview = client.get(f"/remedial/groups/{group_id}", headers=_auth(self.student_token))
        self.assertEqual(gview.status_code, 200)
        self.assertNotIn("members", gview.json())
        self.assertIn("student_friendly_reason", gview.json())

        outsider = client.get(f"/remedial/groups/{group_id}", headers=_auth(self.student3_token))
        self.assertEqual(outsider.status_code, 403)

    def test_individual_intervention_and_status(self):
        created = client.post(
            "/remedial/interventions/individual",
            headers=_auth(self.faculty_token),
            json={"course_id": self.course_id, "learning_gap_id": self.gap3},
        )
        self.assertEqual(created.status_code, 201, created.text)
        iid = created.json()["id"]
        self.assertEqual(created.json()["mode"], "INDIVIDUAL")
        self.assertIn("priority_explanation", created.json())

        act = client.post(
            f"/remedial/interventions/{iid}/activate",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(act.status_code, 200, act.text)
        self.assertEqual(act.json()["status"], "ASSIGNED")
        self.assertIsNotNone(act.json()["learning_session_id"])

        # Other student cannot see
        denied = client.get(
            f"/remedial/interventions/{iid}",
            headers=_auth(self.student_token),
        )
        self.assertEqual(denied.status_code, 403)

        mine = client.get("/remedial/me", headers=_auth(self.student3_token))
        self.assertEqual(mine.status_code, 200)
        ids = {i["id"] for i in mine.json()["interventions"]}
        self.assertIn(iid, ids)
        # Student-friendly explanation only
        own = next(i for i in mine.json()["interventions"] if i["id"] == iid)
        self.assertIn("why_assigned", own["explanation"])

        done = client.patch(
            f"/remedial/interventions/{iid}",
            headers=_auth(self.faculty_token),
            json={"status": "IN_PROGRESS"},
        )
        self.assertEqual(done.status_code, 200)
        done = client.patch(
            f"/remedial/interventions/{iid}",
            headers=_auth(self.faculty_token),
            json={"status": "COMPLETED", "reassessment_required": True},
        )
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["status"], "COMPLETED")
        self.assertTrue(done.json()["reassessment_required"])

        mark = client.patch(
            f"/remedial/interventions/{iid}",
            headers=_auth(self.faculty_token),
            json={"reassessment_completed": True, "outcome": "IMPROVING"},
        )
        self.assertEqual(mark.status_code, 200)
        self.assertEqual(mark.json()["outcome"], "IMPROVING")
        self.assertTrue(mark.json()["reassessment_completed"])

    def test_gaps_list_and_priority(self):
        gaps = client.get(
            f"/remedial/courses/{self.course_id}/gaps",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(gaps.status_code, 200)
        self.assertTrue(len(gaps.json()) >= 3)

        pri = client.get(
            f"/remedial/courses/{self.course_id}/gaps/prioritized",
            headers=_auth(self.faculty_token),
            params={"student_id": self.student3_id},
        )
        self.assertEqual(pri.status_code, 200)
        self.assertEqual(pri.json()[0]["priority_rank"], 1)
        self.assertIn("priority_explanation", pri.json()[0])

        # Student only own gaps
        sg = client.get(
            f"/remedial/courses/{self.course_id}/gaps",
            headers=_auth(self.student_token),
        )
        self.assertEqual(sg.status_code, 200)
        self.assertTrue(all(g["student_id"] == self.student_id for g in sg.json()))


if __name__ == "__main__":
    unittest.main()
