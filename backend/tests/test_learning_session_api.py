"""
P0-013.2 Learning Session Management API tests.
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

client = TestClient(app)
_users = ProtectedUserFactory(client, "P0132")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class LearningSessionAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P0132A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P0132F"})
        cls.other_faculty_token, cls.other_faculty_id = _register_login(
            "faculty", {"employee_code": "P0132F2"}
        )
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P0132S"})
        cls.student2_token, cls.student2_id = _register_login("student", {"roll_number": "P0132S2"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P013.2 Course", "description": "api"},
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
            json={"name": f"Sub-{uuid.uuid4().hex[:6]}", "course_id": cls.course_id},
        )
        assert sub.status_code == 201
        cls.subject_id = sub.json()["id"]
        topic = client.post(
            "/topics",
            headers=_auth(cls.admin_token),
            json={"name": "API Topic", "subject_id": cls.subject_id},
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

    def test_unauthenticated_rejected(self):
        self.assertEqual(client.get("/learning-sessions").status_code, 401)
        self.assertEqual(client.post("/learning-sessions", json={}).status_code, 401)

    def test_create_list_get_update_lifecycle_and_children(self):
        # Unauthorized faculty cannot create
        denied = client.post(
            "/learning-sessions",
            headers=_auth(self.other_faculty_token),
            json={
                "title": "Nope",
                "mode": "COMMON",
                "course_id": self.course_id,
            },
        )
        self.assertEqual(denied.status_code, 403)

        # Student cannot create
        self.assertEqual(
            client.post(
                "/learning-sessions",
                headers=_auth(self.student_token),
                json={"title": "Nope", "mode": "COMMON", "course_id": self.course_id},
            ).status_code,
            403,
        )

        created = client.post(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            json={
                "title": "Common API Session",
                "description": "desc",
                "mode": "COMMON",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "topic_id": self.topic_id,
                "created_by": self.student_id,  # spoof attempt — ignored by design
                "facilitator_id": self.student_id,  # non-admin spoof ignored
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        sid = created.json()["id"]
        self.assertEqual(created.json()["created_by"], self.faculty_id)
        self.assertEqual(created.json()["facilitator_id"], self.faculty_id)
        self.assertEqual(created.json()["status"], "DRAFT")

        # List authorized
        listing = client.get(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(s["id"] == sid for s in listing.json()))

        # Other faculty list excludes
        other_list = client.get("/learning-sessions", headers=_auth(self.other_faculty_token))
        self.assertEqual(other_list.status_code, 200)
        self.assertFalse(any(s["id"] == sid for s in other_list.json()))

        # Get by id
        got = client.get(f"/learning-sessions/{sid}", headers=_auth(self.faculty_token))
        self.assertEqual(got.status_code, 200)

        # Unrelated student cannot get
        self.assertEqual(
            client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token)).status_code,
            403,
        )

        # Update
        upd = client.patch(
            f"/learning-sessions/{sid}",
            headers=_auth(self.faculty_token),
            json={"title": "Updated Title", "description": "new"},
        )
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.json()["title"], "Updated Title")

        # Participants
        add_p = client.post(
            f"/learning-sessions/{sid}/participants",
            headers=_auth(self.faculty_token),
            json={"user_id": self.student_id, "role": "STUDENT"},
        )
        self.assertEqual(add_p.status_code, 201, add_p.text)
        pid = add_p.json()["id"]
        dup = client.post(
            f"/learning-sessions/{sid}/participants",
            headers=_auth(self.faculty_token),
            json={"user_id": self.student_id, "role": "STUDENT"},
        )
        self.assertEqual(dup.status_code, 409)

        # Student cannot add participants
        self.assertEqual(
            client.post(
                f"/learning-sessions/{sid}/participants",
                headers=_auth(self.student_token),
                json={"user_id": self.student2_id},
            ).status_code,
            403,
        )

        # Student can now view
        self.assertEqual(
            client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token)).status_code,
            200,
        )
        # Other student still denied
        self.assertEqual(
            client.get(f"/learning-sessions/{sid}", headers=_auth(self.student2_token)).status_code,
            403,
        )

        # Objectives
        obj = client.post(
            f"/learning-sessions/{sid}/objectives",
            headers=_auth(self.faculty_token),
            json={"statement": "Learn API concepts", "topic_id": self.topic_id},
        )
        self.assertEqual(obj.status_code, 201, obj.text)
        oid = obj.json()["id"]
        objs = client.get(f"/learning-sessions/{sid}/objectives", headers=_auth(self.faculty_token))
        self.assertEqual(objs.status_code, 200)
        self.assertTrue(any(o["id"] == oid for o in objs.json()))

        # Activities
        act = client.post(
            f"/learning-sessions/{sid}/activities",
            headers=_auth(self.faculty_token),
            json={"activity_type": "LECTURE", "title": "Intro", "scope": "COMMON", "sequence": 1},
        )
        self.assertEqual(act.status_code, 201, act.text)
        aid = act.json()["id"]
        patched = client.patch(
            f"/learning-sessions/{sid}/activities/{aid}",
            headers=_auth(self.faculty_token),
            json={"title": "Intro Updated", "status": "READY"},
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["title"], "Intro Updated")

        # Lifecycle start (DRAFT -> READY -> IN_PROGRESS)
        start = client.post(f"/learning-sessions/{sid}/start", headers=_auth(self.faculty_token))
        self.assertEqual(start.status_code, 200, start.text)
        self.assertEqual(start.json()["status"], "IN_PROGRESS")

        # Invalid transition
        bad = client.post(
            f"/learning-sessions/{sid}/transition",
            headers=_auth(self.faculty_token),
            json={"status": "DRAFT"},
        )
        self.assertEqual(bad.status_code, 422)

        # Evidence
        ev = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.faculty_token),
            json={
                "event_type": "ACTIVITY_COMPLETED",
                "user_id": self.student_id,
                "participant_id": pid,
                "activity_id": aid,
                "payload": {"ok": True},
            },
        )
        self.assertEqual(ev.status_code, 201, ev.text)
        evs = client.get(f"/learning-sessions/{sid}/evidence", headers=_auth(self.faculty_token))
        self.assertEqual(evs.status_code, 200)
        self.assertGreaterEqual(len(evs.json()), 1)

        # Pause / resume / complete
        self.assertEqual(
            client.post(f"/learning-sessions/{sid}/pause", headers=_auth(self.faculty_token)).json()[
                "status"
            ],
            "PAUSED",
        )
        self.assertEqual(
            client.post(f"/learning-sessions/{sid}/resume", headers=_auth(self.faculty_token)).json()[
                "status"
            ],
            "IN_PROGRESS",
        )
        done = client.post(f"/learning-sessions/{sid}/complete", headers=_auth(self.faculty_token))
        self.assertEqual(done.status_code, 200)
        self.assertEqual(done.json()["status"], "COMPLETED")

        # Closed session cannot update
        self.assertEqual(
            client.patch(
                f"/learning-sessions/{sid}",
                headers=_auth(self.faculty_token),
                json={"title": "Nope"},
            ).status_code,
            400,
        )

        # Delete objective rejected on closed
        self.assertEqual(
            client.delete(
                f"/learning-sessions/{sid}/objectives/{oid}",
                headers=_auth(self.faculty_token),
            ).status_code,
            400,
        )

        # Nonexistent
        self.assertEqual(
            client.get("/learning-sessions/99999999", headers=_auth(self.faculty_token)).status_code,
            404,
        )

    def test_individual_and_hybrid_api(self):
        ind = client.post(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            json={
                "title": "Individual API",
                "mode": "INDIVIDUAL",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
                "primary_student_id": self.student_id,
            },
        )
        self.assertEqual(ind.status_code, 201, ind.text)
        sid = ind.json()["id"]
        # Second student rejected
        self.assertEqual(
            client.post(
                f"/learning-sessions/{sid}/participants",
                headers=_auth(self.faculty_token),
                json={"user_id": self.student2_id},
            ).status_code,
            422,
        )
        # Student can view own individual session
        self.assertEqual(
            client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token)).status_code,
            200,
        )
        self.assertEqual(
            client.get(f"/learning-sessions/{sid}", headers=_auth(self.student2_token)).status_code,
            403,
        )

        hyb = client.post(
            "/learning-sessions",
            headers=_auth(self.faculty_token),
            json={
                "title": "Hybrid API",
                "mode": "HYBRID",
                "course_id": self.course_id,
                "subject_id": self.subject_id,
            },
        )
        self.assertEqual(hyb.status_code, 201, hyb.text)
        hid = hyb.json()["id"]
        p = client.post(
            f"/learning-sessions/{hid}/participants",
            headers=_auth(self.faculty_token),
            json={"user_id": self.student_id},
        )
        self.assertEqual(p.status_code, 201)
        specific = client.post(
            f"/learning-sessions/{hid}/activities",
            headers=_auth(self.faculty_token),
            json={
                "activity_type": "PRACTICE",
                "title": "Personal practice",
                "scope": "PARTICIPANT_SPECIFIC",
                "participant_id": p.json()["id"],
            },
        )
        self.assertEqual(specific.status_code, 201, specific.text)
        self.assertEqual(specific.json()["scope"], "PARTICIPANT_SPECIFIC")


if __name__ == "__main__":
    unittest.main()
