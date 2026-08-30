"""Phase D integration tests: locked cards, evidence, weightages and resume."""
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app import database, models
from app.main import app
from app.services.learning_workspace import summary
from tests.auth_helpers import ProtectedUserFactory

client = TestClient(app)
users = ProtectedUserFactory(client, "PHASED")


class PhaseDWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = users.create("admin")
        cls.student = users.create("student", {"roll_number": "D-" + uuid.uuid4().hex[:10]})
        cls.other = users.create("student", {"roll_number": "D-" + uuid.uuid4().hex[:10]})

    def setUp(self):
        self.db = database.SessionLocal(); self.addCleanup(self.db.close)
        self.course = models.Course(title="Workspace", programme_code=uuid.uuid4().hex[:10], publication_status="PUBLISHED", is_active=True,
                                    syllabus_url="https://example.com/private-draft", created_by=self.admin.user_id)
        self.db.add(self.course); self.db.flush()
        self.subject = models.Subject(name="Science", course_id=self.course.id)
        self.db.add(self.subject); self.db.flush()
        self.unit = models.Unit(name="Unit One", subject_id=self.subject.id, sequence=1)
        self.db.add(self.unit); self.db.flush()
        self.topics = [models.Topic(name=name, subject_id=self.subject.id, unit_id=self.unit.id) for name in ("First", "Second")]
        self.db.add_all(self.topics)
        self.enrollment = models.StudentCourseEnrollment(student_id=self.student.user_id, course_id=self.course.id, status="ACTIVE")
        self.db.add(self.enrollment); self.db.commit()
        self.headers = {"Authorization": f"Bearer {self.student.token}"}

    def session(self, topic, *, mode="INDIVIDUAL", state="IN_PROGRESS", completed=False, subtopic=None, evidence_time=None, student_id=None):
        user_id = student_id or self.student.user_id
        session = models.LearningSession(title="Lesson", course_id=self.course.id, subject_id=self.subject.id, topic_id=topic.id,
            subtopic_id=subtopic, mode=mode, status=state, created_by=self.admin.user_id)
        self.db.add(session); self.db.flush()
        self.db.add(models.LearningSessionParticipant(session_id=session.id, user_id=user_id, role="STUDENT", status="COMPLETED" if completed else "INVITED"))
        if evidence_time:
            self.db.add(models.LearningEvidence(session_id=session.id, user_id=user_id, event_type="TEACHING_STEP_REACHED", created_at=evidence_time))
        self.db.commit(); return session

    def test_pending_card_is_visible_locked_and_draft_materials_are_hidden(self):
        self.enrollment.status = "PENDING_ACTIVATION"
        self.course.publication_status, self.course.is_active = "DRAFT", False
        self.db.commit()
        response = client.get("/courses/me", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        card = next(c for c in response.json()["enrollments"] if c["id"] == self.course.id)
        self.assertFalse(card["can_access"]); self.assertIsNone(card["learning"])
        self.assertNotIn("syllabus_url", card)
        self.assertEqual(client.get(f"/courses/{self.course.id}/workspace", headers=self.headers).status_code, 403)
        catalog = client.get("/courses/?active_only=false", headers=self.headers).json()
        self.assertNotIn(self.course.id, [c["id"] for c in catalog])

    def test_empty_learning_and_partial_completion_do_not_claim_course_complete(self):
        self.assertEqual(summary(self.db, self.student.user_id, self.course.id)["status"], "NOT_STARTED")
        self.session(self.topics[0], state="COMPLETED", completed=True)
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["completed_topics"], 1)
        self.assertEqual(data["progress_percent"], 50)
        self.assertEqual(data["status"], "IN_PROGRESS")

    def test_group_completion_does_not_complete_an_invited_student(self):
        self.session(self.topics[0], mode="COMMON", state="COMPLETED")
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["completed_topics"], 0)
        self.assertEqual(data["status"], "NOT_STARTED")

    def test_continue_uses_latest_personal_evidence_not_creation_id(self):
        now = datetime.now(timezone.utc)
        recent = self.session(self.topics[0], evidence_time=now)
        self.session(self.topics[1], evidence_time=now - timedelta(days=2))
        self.session(self.topics[1], student_id=self.other.user_id, evidence_time=now + timedelta(days=1))
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["continue_learning"]["session_id"], recent.id)

    def test_subtopics_roll_up_only_when_all_are_complete(self):
        subs = [models.Subtopic(name=n, topic_id=self.topics[0].id) for n in ("A", "B")]
        self.db.add_all(subs); self.db.commit()
        self.session(self.topics[0], state="COMPLETED", completed=True, subtopic=subs[0].id)
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["completed_topics"], 0)
        self.session(self.topics[0], state="COMPLETED", completed=True, subtopic=subs[1].id)
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["completed_topics"], 1)
        self.assertIsNone(data["continue_learning"])

    def test_weightages_are_actual_configuration_and_missing_remains_null(self):
        self.db.add(models.TopicWeightage(subject_id=self.subject.id, topic_id=self.topics[0].id, weight_percent=70))
        self.db.commit()
        response = client.get(f"/courses/{self.course.id}/workspace", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        topics = response.json()["syllabus"][0]["units"][0]["topics"]
        weights = {t["id"]: t["weight_percent"] for t in topics}
        self.assertEqual(weights[self.topics[0].id], 70)
        self.assertIsNone(weights[self.topics[1].id])

    def test_removed_participant_does_not_supply_progress(self):
        session = self.session(self.topics[0], state="COMPLETED", completed=True)
        row = self.db.query(models.LearningSessionParticipant).filter_by(session_id=session.id).one()
        row.status = "REMOVED"; self.db.commit()
        self.assertEqual(summary(self.db, self.student.user_id, self.course.id)["completed_topics"], 0)

    def test_archiving_completed_session_preserves_completion_and_full_course_status(self):
        self.session(self.topics[0], state="ARCHIVED", completed=True)
        self.session(self.topics[1], state="COMPLETED", completed=True)
        data = summary(self.db, self.student.user_id, self.course.id)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["progress_percent"], 100)
        self.assertIsNone(data["continue_learning"])


if __name__ == "__main__":
    unittest.main()
