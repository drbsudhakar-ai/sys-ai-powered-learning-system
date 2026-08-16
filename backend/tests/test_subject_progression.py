"""
P0-019 Student-controlled subject selection, in-subject topic progression, course balance.
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
from app.services import early_warning as ew
from app.services import subject_progression as sp

client = TestClient(app)
_users = ProtectedUserFactory(client, "P019")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int]:
    identity = _users.create(role, extra)
    return identity.token, identity.user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_mastery(student_id: int, course_id: int, topic_id: int, subject_id: int, status: str) -> None:
    db = database.SessionLocal()
    try:
        row = (
            db.query(models.TopicMasteryState)
            .filter(
                models.TopicMasteryState.student_id == student_id,
                models.TopicMasteryState.course_id == course_id,
                models.TopicMasteryState.topic_id == topic_id,
            )
            .first()
        )
        if row:
            row.status = status
            row.indicator = "GREEN" if status == "MASTERED" else "YELLOW"
            row.subject_id = subject_id
        else:
            db.add(
                models.TopicMasteryState(
                    student_id=student_id,
                    course_id=course_id,
                    topic_id=topic_id,
                    subject_id=subject_id,
                    status=status,
                    indicator="GREEN" if status == "MASTERED" else "YELLOW",
                )
            )
        db.commit()
    finally:
        db.close()


class SubjectProgressionAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id = _register_login("admin", {"employee_code": "P019A"})
        cls.faculty_token, cls.faculty_id = _register_login("faculty", {"employee_code": "P019F"})
        cls.student_token, cls.student_id = _register_login("student", {"roll_number": "P019S"})
        cls.other_token, cls.other_id = _register_login("student", {"roll_number": "P019X"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P019 NEET", "description": "subject freedom"},
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

        def subject(name: str) -> int:
            res = client.post(
                "/admin/subjects",
                headers=_auth(cls.admin_token),
                json={"name": f"{name}-{uuid.uuid4().hex[:5]}", "course_id": cls.course_id},
            )
            assert res.status_code == 201, res.text
            return res.json()["id"]

        def topic(name: str, subject_id: int) -> int:
            res = client.post(
                "/topics",
                headers=_auth(cls.admin_token),
                json={"name": name, "subject_id": subject_id},
            )
            assert res.status_code == 201, res.text
            return res.json()["id"]

        cls.phy_id = subject("Physics")
        cls.chem_id = subject("Chemistry")
        cls.bio_id = subject("Biology")

        cls.units = topic("Units & Measurements", cls.phy_id)
        cls.motion = topic("Motion", cls.phy_id)
        cls.laws = topic("Laws of Motion", cls.phy_id)
        cls.work = topic("Work, Energy & Power", cls.phy_id)
        cls.potential = topic("Electric Potential", cls.phy_id)
        cls.cap = topic("Capacitance", cls.phy_id)

        cls.atomic = topic("Atomic Structure", cls.chem_id)
        cls.bonding = topic("Chemical Bonding", cls.chem_id)
        cls.org = topic("Organic Chemistry", cls.chem_id)

        cls.cell = topic("Cell Biology", cls.bio_id)
        cls.genetics = topic("Genetics", cls.bio_id)
        cls.ecology = topic("Ecology", cls.bio_id)

        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.student_token)).status_code
            == 201
        )
        assert (
            client.post(f"/courses/{cls.course_id}/enroll", headers=_auth(cls.other_token)).status_code
            == 201
        )

        prereq = client.post(
            f"/topics/{cls.laws}/prerequisites",
            headers=_auth(cls.admin_token),
            json={"prerequisite_topic_id": cls.motion},
        )
        assert prereq.status_code == 201, prereq.text
        cap_pr = client.post(
            f"/topics/{cls.cap}/prerequisites",
            headers=_auth(cls.admin_token),
            json={"prerequisite_topic_id": cls.potential},
        )
        assert cap_pr.status_code == 201, cap_pr.text

        _set_mastery(cls.student_id, cls.course_id, cls.units, cls.phy_id, "MASTERED")
        _set_mastery(cls.student_id, cls.course_id, cls.motion, cls.phy_id, "MASTERED")

    def test_student_can_access_any_enrolled_subject(self):
        res = client.get(
            "/learning-journey/me/subjects",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertFalse(data["subject_order_imposed"])
        ids = {s["id"] for s in data["subjects"]}
        self.assertEqual(ids, {self.phy_id, self.chem_id, self.bio_id})
        for sid in ids:
            view = client.get(
                f"/learning-journey/me/subjects/{sid}",
                headers=_auth(self.student_token),
                params={"course_id": self.course_id},
            )
            self.assertEqual(view.status_code, 200, view.text)
            self.assertFalse(view.json()["subject_order_imposed"])

    def test_no_course_wide_subject_order(self):
        j = client.get(
            "/learning-journey/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(j.status_code, 200, j.text)
        self.assertFalse(j.json()["subject_order_imposed"])
        nxt = client.get(
            f"/learning-journey/me/subjects/{self.bio_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(nxt.status_code, 200, nxt.text)
        rec = nxt.json()["recommended"]
        self.assertEqual(rec["topic_id"], self.cell)
        self.assertNotEqual(rec["topic_id"], self.laws)

    def test_recommended_topic_is_inside_selected_subject(self):
        nxt = client.get(
            f"/learning-journey/me/subjects/{self.phy_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(nxt.status_code, 200, nxt.text)
        rec = nxt.json()
        self.assertEqual(rec["recommended"]["topic_id"], self.laws)
        self.assertIn("Motion", rec["reason"])
        self.assertTrue(all(t["topic_id"] in {
            self.units, self.motion, self.laws, self.work, self.potential, self.cap
        } for t in rec["topics"]))

    def test_mastered_topics_are_skipped(self):
        nxt = client.get(
            f"/learning-journey/me/subjects/{self.phy_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        rec_id = nxt.json()["recommended"]["topic_id"]
        self.assertNotIn(rec_id, (self.units, self.motion))

    def test_prerequisite_warning_is_advisory(self):
        choose = client.post(
            f"/learning-journey/me/subjects/{self.phy_id}/topics/choose",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
            json={"topic_id": self.cap},
        )
        self.assertEqual(choose.status_code, 200, choose.text)
        data = choose.json()
        self.assertTrue(data["override"])
        self.assertEqual(data["teaching_target"]["topic_id"], self.cap)
        self.assertFalse(data["prerequisite_warning"]["blocking"])
        self.assertFalse(data["prerequisite_warning"]["satisfied"])
        self.assertIn("Electric Potential", data["prerequisite_warning"]["message"])
        self.assertEqual(data["href"], "/learning-sessions")

    def test_prerequisite_satisfied_topic_is_recommended(self):
        nxt = client.get(
            f"/learning-journey/me/subjects/{self.phy_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(nxt.json()["recommended"]["topic_id"], self.laws)
        warning = nxt.json()["prerequisite_warning"]
        self.assertTrue(warning["has_authoritative_prerequisites"])
        self.assertTrue(warning.get("satisfied"))

    def test_recommendation_updates_after_mastery(self):
        _set_mastery(self.student_id, self.course_id, self.laws, self.phy_id, "MASTERED")
        try:
            nxt = client.get(
                f"/learning-journey/me/subjects/{self.phy_id}/next",
                headers=_auth(self.student_token),
                params={"course_id": self.course_id},
            )
            self.assertEqual(nxt.status_code, 200, nxt.text)
            self.assertNotEqual(nxt.json()["recommended"]["topic_id"], self.laws)
            self.assertEqual(nxt.json()["recommended"]["topic_id"], self.work)
        finally:
            _set_mastery(self.student_id, self.course_id, self.laws, self.phy_id, "NOT_ASSESSED")
            _set_mastery(self.student_id, self.course_id, self.units, self.phy_id, "MASTERED")
            _set_mastery(self.student_id, self.course_id, self.motion, self.phy_id, "MASTERED")

    def test_switching_subjects_does_not_alter_other_progression(self):
        phy = client.get(
            f"/learning-journey/me/subjects/{self.phy_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        phy_rec = phy.json()["recommended"]["topic_id"]
        bio = client.get(
            f"/learning-journey/me/subjects/{self.bio_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(bio.json()["recommended"]["topic_id"], self.cell)
        phy_again = client.get(
            f"/learning-journey/me/subjects/{self.phy_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(phy_again.json()["recommended"]["topic_id"], phy_rec)

    def test_return_to_subject_restores_recommendation_context(self):
        client.post(
            f"/learning-journey/me/subjects/{self.phy_id}/focus",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        client.post(
            f"/learning-journey/me/subjects/{self.chem_id}/focus",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        back = client.get(
            "/learning-journey/me",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id, "subject_id": self.phy_id},
        )
        self.assertEqual(back.status_code, 200, back.text)
        rec = back.json()["subject_guidance"]["recommended_topic"]
        self.assertEqual(rec["topic_id"], self.laws)
        self.assertEqual(back.json()["subject_guidance"]["selected_subject"]["id"], self.phy_id)

    def test_balanced_subjects_do_not_warn(self):
        bal = client.get(
            f"/analytics/me/courses/{self.course_id}/balance",
            headers=_auth(self.other_token),
        )
        self.assertEqual(bal.status_code, 200, bal.text)
        self.assertEqual(bal.json()["balance_status"], "BALANCED")
        self.assertIsNone(bal.json()["signal"])
        self.assertTrue(bal.json()["does_not_force_subject_switch"] if "does_not_force_subject_switch" in bal.json() else True)
        self.assertFalse(bal.json()["subject_order_imposed"])

    def test_persistent_imbalance_produces_explainable_signal(self):
        for tid in (self.units, self.motion, self.laws, self.work, self.potential, self.cap):
            _set_mastery(self.student_id, self.course_id, tid, self.phy_id, "MASTERED")
        for tid in (self.atomic, self.bonding, self.org):
            _set_mastery(self.student_id, self.course_id, tid, self.chem_id, "MASTERED")
        try:
            bal = client.get(
                f"/analytics/me/courses/{self.course_id}/balance",
                headers=_auth(self.student_token),
            )
            self.assertEqual(bal.status_code, 200, bal.text)
            data = bal.json()
            self.assertIn(data["balance_status"], ("WATCH", "ATTENTION_REQUIRED", "URGENT_ATTENTION"))
            self.assertEqual(data["lagging_subject"]["subject_id"], self.bio_id)
            self.assertTrue(data["evidence"])
            self.assertFalse(data["subject_order_imposed"])
            self.assertIn("Biology", data["reason"] or data["lagging_subject"]["subject_name"])
            sig = data["signal"]
            self.assertEqual(sig["code"], "SUBJECT_PROGRESS_IMBALANCE")
            self.assertTrue(sig["does_not_force_subject_switch"])
            self.assertIn("P0-015_TopicMasteryState", sig["source_of_truth"])

            warnings = ew.evaluate_student_warnings(
                database.SessionLocal(), student_id=self.student_id, course_id=self.course_id
            )
            self.assertTrue(any(w["code"] == "SUBJECT_PROGRESS_IMBALANCE" for w in warnings))

            # warning does not force subject switch — biology remains freely selectable
            bio = client.get(
                f"/learning-journey/me/subjects/{self.bio_id}",
                headers=_auth(self.student_token),
                params={"course_id": self.course_id},
            )
            self.assertEqual(bio.status_code, 200, bio.text)
            self.assertEqual(bio.json()["selected_subject"]["id"], self.bio_id)
        finally:
            for tid in (self.laws, self.work, self.potential, self.cap):
                _set_mastery(self.student_id, self.course_id, tid, self.phy_id, "NOT_ASSESSED")
            for tid in (self.atomic, self.bonding, self.org):
                _set_mastery(self.student_id, self.course_id, tid, self.chem_id, "NOT_ASSESSED")
            _set_mastery(self.student_id, self.course_id, self.units, self.phy_id, "MASTERED")
            _set_mastery(self.student_id, self.course_id, self.motion, self.phy_id, "MASTERED")

    def test_imbalance_notification_is_not_repeated(self):
        for tid in (self.units, self.motion, self.laws, self.work, self.potential, self.cap):
            _set_mastery(self.student_id, self.course_id, tid, self.phy_id, "MASTERED")
        for tid in (self.atomic, self.bonding, self.org):
            _set_mastery(self.student_id, self.course_id, tid, self.chem_id, "MASTERED")
        db = database.SessionLocal()
        try:
            before = (
                db.query(models.Notification)
                .filter(
                    models.Notification.student_id == self.student_id,
                    models.Notification.event == "SUBJECT_PROGRESS_IMBALANCE",
                )
                .count()
            )
            bal = sp.evaluate_course_balance(db, student_id=self.student_id, course_id=self.course_id)
            self.assertIsNotNone(bal.get("signal"))
            first = sp.maybe_notify_imbalance(
                db, student_id=self.student_id, course_id=self.course_id, balance=bal
            )
            second = sp.maybe_notify_imbalance(
                db, student_id=self.student_id, course_id=self.course_id, balance=bal
            )
            after = (
                db.query(models.Notification)
                .filter(
                    models.Notification.student_id == self.student_id,
                    models.Notification.event == "SUBJECT_PROGRESS_IMBALANCE",
                )
                .count()
            )
            self.assertTrue(first or after > before)
            self.assertFalse(second)
            self.assertLessEqual(after, before + 1)
        finally:
            db.close()
            for tid in (self.laws, self.work, self.potential, self.cap):
                _set_mastery(self.student_id, self.course_id, tid, self.phy_id, "NOT_ASSESSED")
            for tid in (self.atomic, self.bonding, self.org):
                _set_mastery(self.student_id, self.course_id, tid, self.chem_id, "NOT_ASSESSED")
            _set_mastery(self.student_id, self.course_id, self.units, self.phy_id, "MASTERED")
            _set_mastery(self.student_id, self.course_id, self.motion, self.phy_id, "MASTERED")

    def test_students_see_only_own_data(self):
        mine = client.get(
            "/learning-journey/me",
            headers=_auth(self.other_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(mine.status_code, 200, mine.text)
        self.assertEqual(mine.json()["student_id"], self.other_id)
        peer = client.get(
            f"/learning-journey/faculty/students/{self.student_id}",
            headers=_auth(self.other_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(peer.status_code, 403)

    def test_faculty_and_admin_balance_scope(self):
        fac = client.get(
            f"/analytics/faculty/courses/{self.course_id}/balance",
            headers=_auth(self.faculty_token),
        )
        self.assertEqual(fac.status_code, 200, fac.text)
        self.assertIn("status_counts", fac.json())
        student_forbidden = client.get(
            f"/analytics/faculty/courses/{self.course_id}/balance",
            headers=_auth(self.student_token),
        )
        self.assertEqual(student_forbidden.status_code, 403)
        admin = client.get(
            "/analytics/admin/balance",
            headers=_auth(self.admin_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(admin.status_code, 200, admin.text)
        self.assertTrue(admin.json()["courses"])
        student_admin = client.get(
            "/analytics/admin/balance",
            headers=_auth(self.student_token),
        )
        self.assertEqual(student_admin.status_code, 403)

    def test_same_subject_prerequisite_only(self):
        bad = client.post(
            f"/topics/{self.laws}/prerequisites",
            headers=_auth(self.admin_token),
            json={"prerequisite_topic_id": self.cell},
        )
        self.assertEqual(bad.status_code, 422)

    def test_no_prereq_metadata_does_not_invent_edges(self):
        nxt = client.get(
            f"/learning-journey/me/subjects/{self.chem_id}/next",
            headers=_auth(self.student_token),
            params={"course_id": self.course_id},
        )
        self.assertEqual(nxt.status_code, 200, nxt.text)
        warning = nxt.json()["prerequisite_warning"]
        self.assertFalse(warning["has_authoritative_prerequisites"])
        self.assertIn("cannot establish a prerequisite confidently", warning["message"])


if __name__ == "__main__":
    unittest.main()
