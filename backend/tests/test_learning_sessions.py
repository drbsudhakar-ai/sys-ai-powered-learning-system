"""
P0-013.1 Learning Session domain & persistence foundation tests.
Exercises service layer (full HTTP API deferred to P0-013.2).
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app import models, database
from app.services import learning_sessions as ls

client = TestClient(app)


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register_login(role: str, extra: dict) -> tuple[str, int, models.User]:
    email = _email(role)
    payload = {
        "name": f"P013 {role}",
        "email": email,
        "role": role,
        "password": "TestPass123!",
        **extra,
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post("/auth/login", data={"username": email, "password": "TestPass123!"})
    assert login.status_code == 200, login.text
    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == reg.json()["id"]).first()
        db.expunge(user)
    finally:
        db.close()
    return login.json()["access_token"], reg.json()["id"], user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user(db, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()


class LearningSessionDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_token, cls.admin_id, _ = _register_login("admin", {"employee_code": "P013A"})
        cls.faculty_token, cls.faculty_id, _ = _register_login("faculty", {"employee_code": "P013F"})
        cls.other_faculty_token, cls.other_faculty_id, _ = _register_login(
            "faculty", {"employee_code": "P013F2"}
        )
        cls.student_token, cls.student_id, _ = _register_login("student", {"roll_number": "P013S"})
        cls.student2_token, cls.student2_id, _ = _register_login("student", {"roll_number": "P013S2"})

        course = client.post(
            "/courses/",
            headers=_auth(cls.admin_token),
            json={"title": "P013 Course", "description": "learning sessions"},
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
            json={"name": "Intro", "subject_id": cls.subject_id},
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

    def test_common_session_lifecycle_participants_objectives_activities_evidence(self):
        db = database.SessionLocal()
        try:
            faculty = _user(db, self.faculty_id)
            session = ls.create_session(
                db,
                faculty,
                title="Common Lecture 1",
                course_id=self.course_id,
                mode="COMMON",
                subject_id=self.subject_id,
                topic_id=self.topic_id,
                description="Class lecture",
            )
            self.assertEqual(session.mode, "COMMON")
            self.assertEqual(session.status, "DRAFT")
            self.assertTrue(any(p.role in ("FACILITATOR", "TEACHER") for p in session.participants))

            p1 = ls.add_participant(db, faculty, session.id, user_id=self.student_id, role="STUDENT")
            p2 = ls.add_participant(db, faculty, session.id, user_id=self.student2_id, role="STUDENT")
            self.assertEqual(p1.status, "INVITED")

            with self.assertRaises(HTTPException) as dup:
                ls.add_participant(db, faculty, session.id, user_id=self.student_id, role="STUDENT")
            self.assertEqual(dup.exception.status_code, 409)

            obj = ls.add_objective(
                db,
                faculty,
                session.id,
                statement="Understand Newton's first law",
                topic_id=self.topic_id,
                concept_tag="Newton",
            )
            self.assertEqual(obj.status, "PENDING")

            act = ls.add_activity(
                db,
                faculty,
                session.id,
                activity_type="LECTURE",
                title="Intro lecture",
                scope="COMMON",
            )
            self.assertEqual(act.scope, "COMMON")

            session = ls.transition_status(db, faculty, session.id, "READY")
            self.assertEqual(session.status, "READY")
            session = ls.transition_status(db, faculty, session.id, "IN_PROGRESS")
            self.assertEqual(session.status, "IN_PROGRESS")
            self.assertIsNotNone(session.actual_start)

            with self.assertRaises(HTTPException) as bad:
                ls.transition_status(db, faculty, session.id, "DRAFT")
            self.assertEqual(bad.exception.status_code, 422)

            ev = ls.record_evidence(
                db,
                faculty,
                session_id=session.id,
                event_type="ACTIVITY_COMPLETED",
                user_id=self.student_id,
                participant_id=p1.id,
                activity_id=act.id,
                payload={"note": "attended"},
            )
            self.assertEqual(ev.event_type, "ACTIVITY_COMPLETED")

            session = ls.transition_status(db, faculty, session.id, "COMPLETED")
            self.assertEqual(session.status, "COMPLETED")
            self.assertIsNotNone(session.actual_end)

            evidence_count = (
                db.query(models.LearningEvidence)
                .filter(models.LearningEvidence.session_id == session.id)
                .count()
            )
            self.assertGreaterEqual(evidence_count, 2)
        finally:
            db.close()

    def test_individual_and_hybrid_modes(self):
        db = database.SessionLocal()
        try:
            faculty = _user(db, self.faculty_id)
            individual = ls.create_session(
                db,
                faculty,
                title="Individual AI session",
                course_id=self.course_id,
                mode="INDIVIDUAL",
                subject_id=self.subject_id,
                primary_student_id=self.student_id,
            )
            self.assertEqual(individual.mode, "INDIVIDUAL")
            students = [p for p in individual.participants if p.role == "STUDENT"]
            self.assertEqual(len(students), 1)

            with self.assertRaises(HTTPException) as exc:
                ls.add_participant(
                    db, faculty, individual.id, user_id=self.student2_id, role="STUDENT"
                )
            self.assertEqual(exc.exception.status_code, 422)

            hybrid = ls.create_session(
                db,
                faculty,
                title="Hybrid session",
                course_id=self.course_id,
                mode="HYBRID",
                subject_id=self.subject_id,
                topic_id=self.topic_id,
            )
            p = ls.add_participant(db, faculty, hybrid.id, user_id=self.student_id)
            ls.add_activity(
                db,
                faculty,
                hybrid.id,
                activity_type="EXPLANATION",
                title="Common explanation",
                scope="COMMON",
            )
            specific = ls.add_activity(
                db,
                faculty,
                hybrid.id,
                activity_type="PRACTICE",
                title="Personalized practice",
                scope="PARTICIPANT_SPECIFIC",
                participant_id=p.id,
            )
            self.assertEqual(specific.scope, "PARTICIPANT_SPECIFIC")
            self.assertEqual(specific.participant_id, p.id)

            with self.assertRaises(HTTPException):
                ls.add_activity(
                    db,
                    faculty,
                    hybrid.id,
                    activity_type="PRACTICE",
                    title="Missing participant",
                    scope="PARTICIPANT_SPECIFIC",
                )
        finally:
            db.close()

    def test_authorization_foundation(self):
        db = database.SessionLocal()
        try:
            faculty = _user(db, self.faculty_id)
            other = _user(db, self.other_faculty_id)
            student = _user(db, self.student_id)
            student2 = _user(db, self.student2_id)

            with self.assertRaises(HTTPException) as denied:
                ls.create_session(
                    db,
                    other,
                    title="Nope",
                    course_id=self.course_id,
                    mode="COMMON",
                )
            self.assertEqual(denied.exception.status_code, 403)

            with self.assertRaises(HTTPException):
                ls.create_session(
                    db,
                    student,
                    title="Student cannot create",
                    course_id=self.course_id,
                    mode="COMMON",
                )

            session = ls.create_session(
                db,
                faculty,
                title="Authz session",
                course_id=self.course_id,
                mode="INDIVIDUAL",
                primary_student_id=self.student_id,
            )
            self.assertTrue(ls.can_view_session(db, student, session))
            self.assertFalse(ls.can_view_session(db, student2, session))
            self.assertFalse(ls.can_view_session(db, other, session))

            with self.assertRaises(HTTPException) as rem:
                ls.remove_participant(db, other, session.id, session.participants[0].id)
            self.assertEqual(rem.exception.status_code, 403)
        finally:
            db.close()

    def test_invalid_mode_and_unenrolled_student(self):
        db = database.SessionLocal()
        try:
            faculty = _user(db, self.faculty_id)
            with self.assertRaises(HTTPException) as mode:
                ls.create_session(
                    db,
                    faculty,
                    title="Bad mode",
                    course_id=self.course_id,
                    mode="GROUP",
                )
            self.assertEqual(mode.exception.status_code, 422)

            # unenrolled student
            _, sid, _ = _register_login("student", {"roll_number": f"P013U{uuid.uuid4().hex[:4]}"})
            with self.assertRaises(HTTPException) as unen:
                ls.create_session(
                    db,
                    faculty,
                    title="Unenrolled individual",
                    course_id=self.course_id,
                    mode="INDIVIDUAL",
                    primary_student_id=sid,
                )
            self.assertEqual(unen.exception.status_code, 403)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
