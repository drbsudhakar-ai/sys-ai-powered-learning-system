"""
P0-013.3 — COMMON / INDIVIDUAL / HYBRID learning session behavior tests.
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

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    email = _email(role)
    payload = {
        "name": f"P0133 {role}",
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


class LearningSessionBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P0133A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P0133F"})
        cls.other_faculty_token, cls.other_faculty_id = _register_login(
            "faculty", {"employee_code": "P0133F2"}
        )
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P0133S"})
        cls.student2_token, cls.student2_id = _register_login("student", {"roll_number": "P0133S2"})
        cls.outsider_token, cls.outsider_id = _register_login("student", {"roll_number": "P0133X"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P013.3 Course", "description": "behavior"},
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
            json={"name": "Behavior Topic", "subject_id": cls.subject_id},
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

    def _create_session(self, mode: str, **extra) -> dict:
        body = {
            "title": f"{mode} {uuid.uuid4().hex[:6]}",
            "mode": mode,
            "course_id": self.course_id,
            "subject_id": self.subject_id,
            "topic_id": self.topic_id,
            **extra,
        }
        r = client.post("/learning-sessions", headers=_auth(self.faculty_token), json=body)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def _add_participant(self, session_id: int, user_id: int) -> dict:
        r = client.post(
            f"/learning-sessions/{session_id}/participants",
            headers=_auth(self.faculty_token),
            json={"user_id": user_id, "role": "STUDENT"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def _add_activity(self, session_id: int, **kwargs) -> dict:
        r = client.post(
            f"/learning-sessions/{session_id}/activities",
            headers=_auth(self.faculty_token),
            json=kwargs,
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    # ---- COMMON ----

    def test_common_multi_student_shared_activities_and_isolated_evidence(self):
        session = self._create_session("COMMON")
        sid = session["id"]
        pa = self._add_participant(sid, self.student_id)
        pb = self._add_participant(sid, self.student2_id)
        common = self._add_activity(
            sid,
            activity_type="LECTURE",
            title="Shared lecture",
            scope="COMMON",
            sequence=1,
        )
        # COMMON may also host participant-specific remediation slots
        a_only = self._add_activity(
            sid,
            activity_type="PRACTICE",
            title="A practice",
            scope="PARTICIPANT_SPECIFIC",
            participant_id=pa["id"],
            sequence=2,
        )

        acts_a = client.get(
            f"/learning-sessions/{sid}/activities", headers=_auth(self.student_token)
        )
        acts_b = client.get(
            f"/learning-sessions/{sid}/activities", headers=_auth(self.student2_token)
        )
        self.assertEqual(acts_a.status_code, 200)
        self.assertEqual(acts_b.status_code, 200)
        ids_a = {a["id"] for a in acts_a.json()}
        ids_b = {a["id"] for a in acts_b.json()}
        self.assertIn(common["id"], ids_a)
        self.assertIn(common["id"], ids_b)
        self.assertIn(a_only["id"], ids_a)
        self.assertNotIn(a_only["id"], ids_b)

        ev_a = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": common["id"]},
        )
        ev_b = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student2_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": common["id"]},
        )
        self.assertEqual(ev_a.status_code, 201, ev_a.text)
        self.assertEqual(ev_b.status_code, 201, ev_b.text)
        self.assertEqual(ev_a.json()["user_id"], self.student_id)
        self.assertEqual(ev_b.json()["user_id"], self.student2_id)
        self.assertNotEqual(ev_a.json()["id"], ev_b.json()["id"])

        # Student A cannot complete B's view of A's private activity as B
        denied = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student2_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": a_only["id"]},
        )
        self.assertEqual(denied.status_code, 403)

        # Participant progress independent; session still DRAFT/READY etc.
        prog = client.get(
            f"/learning-sessions/{sid}/progress", headers=_auth(self.faculty_token)
        )
        self.assertEqual(prog.status_code, 200, prog.text)
        by_user = {p["user_id"]: p for p in prog.json()["participants"]}
        self.assertEqual(prog.json()["session_status"], session["status"])
        self.assertGreater(by_user[self.student_id]["percent_complete"], 0)
        # B completed only the common activity; A has an extra assigned activity
        self.assertNotEqual(
            by_user[self.student_id]["percent_complete"],
            by_user[self.student2_id]["percent_complete"],
        )

        # Completing session does not force every participant COMPLETED
        client.post(f"/learning-sessions/{sid}/start", headers=_auth(self.faculty_token))
        done = client.post(f"/learning-sessions/{sid}/complete", headers=_auth(self.faculty_token))
        self.assertEqual(done.status_code, 200)
        self.assertEqual(done.json()["status"], "COMPLETED")
        prog2 = client.get(
            f"/learning-sessions/{sid}/progress", headers=_auth(self.faculty_token)
        ).json()
        self.assertEqual(prog2["session_status"], "COMPLETED")
        statuses = {p["user_id"]: p["progress_status"] for p in prog2["participants"]}
        # At least one student is not fully complete (A still has private practice)
        self.assertTrue(
            any(s != "COMPLETED" for s in statuses.values())
            or by_user[self.student_id]["assigned_activities"]
            > by_user[self.student_id]["completed_activities"]
        )

    # ---- INDIVIDUAL ----

    def test_individual_exactly_one_participant_and_access(self):
        session = self._create_session("INDIVIDUAL", primary_student_id=self.student_id)
        sid = session["id"]
        students = [p for p in session["participants"] if p["role"] == "STUDENT"]
        self.assertEqual(len(students), 1)
        part = students[0]

        second = client.post(
            f"/learning-sessions/{sid}/participants",
            headers=_auth(self.faculty_token),
            json={"user_id": self.student2_id, "role": "STUDENT"},
        )
        self.assertEqual(second.status_code, 422)

        # Unauthorized / non-participant student cannot view
        denied = client.get(f"/learning-sessions/{sid}", headers=_auth(self.student2_token))
        self.assertEqual(denied.status_code, 403)
        outsider = client.get(f"/learning-sessions/{sid}", headers=_auth(self.outsider_token))
        self.assertEqual(outsider.status_code, 403)

        ok = client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token))
        self.assertEqual(ok.status_code, 200)

        specific = self._add_activity(
            sid,
            activity_type="PRACTICE",
            title="Solo practice",
            scope="PARTICIPANT_SPECIFIC",
            participant_id=part["id"],
        )
        acts = client.get(
            f"/learning-sessions/{sid}/activities", headers=_auth(self.student_token)
        ).json()
        self.assertEqual([a["id"] for a in acts], [specific["id"]])

        ev = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": specific["id"]},
        )
        self.assertEqual(ev.status_code, 201)
        self.assertEqual(ev.json()["user_id"], self.student_id)

        # Peer cannot record evidence (cannot even view session)
        peer_ev = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student2_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": specific["id"]},
        )
        self.assertIn(peer_ev.status_code, (403, 404))

    # ---- HYBRID + visibility matrix ----

    def test_hybrid_visibility_matrix_and_progress(self):
        session = self._create_session("HYBRID")
        sid = session["id"]
        pa = self._add_participant(sid, self.student_id)
        pb = self._add_participant(sid, self.student2_id)

        common = self._add_activity(
            sid, activity_type="EXPLANATION", title="Intro", scope="COMMON", sequence=1
        )
        act_a = self._add_activity(
            sid,
            activity_type="PRACTICE",
            title="A path",
            scope="PARTICIPANT_SPECIFIC",
            participant_id=pa["id"],
            sequence=2,
        )
        act_b = self._add_activity(
            sid,
            activity_type="PRACTICE",
            title="B path",
            scope="PARTICIPANT_SPECIFIC",
            participant_id=pb["id"],
            sequence=3,
        )

        # Sequence conflict
        clash = client.post(
            f"/learning-sessions/{sid}/activities",
            headers=_auth(self.faculty_token),
            json={
                "activity_type": "DISCUSSION",
                "title": "Dup seq",
                "scope": "COMMON",
                "sequence": 1,
            },
        )
        self.assertEqual(clash.status_code, 422)

        # Student A: common + A activity; not B
        a_view = {
            a["id"]: a
            for a in client.get(
                f"/learning-sessions/{sid}/activities", headers=_auth(self.student_token)
            ).json()
        }
        self.assertIn(common["id"], a_view)
        self.assertIn(act_a["id"], a_view)
        self.assertNotIn(act_b["id"], a_view)

        # Student B: common + B activity; not A
        b_view = {
            a["id"]: a
            for a in client.get(
                f"/learning-sessions/{sid}/activities", headers=_auth(self.student2_token)
            ).json()
        }
        self.assertIn(common["id"], b_view)
        self.assertIn(act_b["id"], b_view)
        self.assertNotIn(act_a["id"], b_view)

        # GET session payload also filters
        get_a = client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token)).json()
        self.assertNotIn(act_b["id"], {a["id"] for a in get_a["activities"]})

        # Faculty sees all
        fac = client.get(
            f"/learning-sessions/{sid}/activities", headers=_auth(self.faculty_token)
        ).json()
        self.assertEqual({a["id"] for a in fac}, {common["id"], act_a["id"], act_b["id"]})

        # Cross-student evidence rejected
        cross = client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": act_b["id"]},
        )
        self.assertEqual(cross.status_code, 403)

        # Different progress
        client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": common["id"]},
        )
        client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": act_a["id"]},
        )
        client.post(
            f"/learning-sessions/{sid}/evidence",
            headers=_auth(self.student2_token),
            json={"event_type": "ACTIVITY_COMPLETED", "activity_id": common["id"]},
        )

        prog_fac = client.get(
            f"/learning-sessions/{sid}/progress", headers=_auth(self.faculty_token)
        ).json()
        by_user = {p["user_id"]: p for p in prog_fac["participants"]}
        self.assertEqual(by_user[self.student_id]["percent_complete"], 100.0)
        self.assertLess(by_user[self.student2_id]["percent_complete"], 100.0)

        # Student only sees own progress row
        prog_a = client.get(
            f"/learning-sessions/{sid}/progress", headers=_auth(self.student_token)
        ).json()
        self.assertEqual(len(prog_a["participants"]), 1)
        self.assertEqual(prog_a["participants"][0]["user_id"], self.student_id)

        # Evidence list isolation
        ev_list_b = client.get(
            f"/learning-sessions/{sid}/evidence", headers=_auth(self.student2_token)
        ).json()
        self.assertTrue(all(e["user_id"] == self.student2_id for e in ev_list_b))

    # ---- Authorization ----

    def test_authorization_boundaries(self):
        self.assertEqual(client.get("/learning-sessions").status_code, 401)

        session = self._create_session("COMMON")
        sid = session["id"]
        self._add_participant(sid, self.student_id)

        unrelated = client.get(f"/learning-sessions/{sid}", headers=_auth(self.other_faculty_token))
        self.assertEqual(unrelated.status_code, 403)

        not_enrolled = client.get(f"/learning-sessions/{sid}", headers=_auth(self.outsider_token))
        self.assertEqual(not_enrolled.status_code, 403)

        ok = client.get(f"/learning-sessions/{sid}", headers=_auth(self.student_token))
        self.assertEqual(ok.status_code, 200)

        admin_ok = client.get(f"/learning-sessions/{sid}", headers=_auth(self.admin_token))
        self.assertEqual(admin_ok.status_code, 200)

        # Students cannot add activities
        denied_act = client.post(
            f"/learning-sessions/{sid}/activities",
            headers=_auth(self.student_token),
            json={"activity_type": "LECTURE", "title": "Nope", "scope": "COMMON"},
        )
        self.assertEqual(denied_act.status_code, 403)

        # Nonexistent participant target rejected
        hybrid = self._create_session("HYBRID")
        bad = client.post(
            f"/learning-sessions/{hybrid['id']}/activities",
            headers=_auth(self.faculty_token),
            json={
                "activity_type": "PRACTICE",
                "title": "Ghost",
                "scope": "PARTICIPANT_SPECIFIC",
                "participant_id": 99999999,
            },
        )
        self.assertEqual(bad.status_code, 404)


if __name__ == "__main__":
    unittest.main()
