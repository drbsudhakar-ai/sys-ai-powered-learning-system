"""P036.1 governed academic-content foundation tests."""
import unittest
import uuid
from fastapi.testclient import TestClient
from app import database, models
from app.main import app
from tests.auth_helpers import ProtectedUserFactory

client = TestClient(app)
users = ProtectedUserFactory(client, "P036")


class AcademicContentFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = users.create("admin")
        cls.expert = users.create("faculty", {"employee_code": "P036-EXPERT"})
        cls.reviewer = users.create("faculty", {"employee_code": "P036-REVIEWER"})
        cls.coordinator = users.create("faculty", {"employee_code": "P036-COORDINATOR"})

    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        with database.SessionLocal() as db:
            self.course = models.Course(title=f"P036 Course {suffix}", programme_code=f"P036-{suffix}",
                created_by=self.admin.user_id)
            db.add(self.course); db.flush()
            self.subject = models.Subject(name=f"Arithmetic {suffix}", course_id=self.course.id)
            db.add(self.subject); db.flush()
            self.topic = models.Topic(name=f"Ratio {suffix}", subject_id=self.subject.id)
            db.add(self.topic); db.flush()
            self.subtopic = models.Subtopic(name=f"Ratio comparison {suffix}", topic_id=self.topic.id)
            db.add(self.subtopic); db.flush()
            db.add(models.SubjectExpertAssignment(faculty_id=self.expert.user_id, subject_id=self.subject.id))
            db.add(models.FacultyCourseAssignment(faculty_id=self.coordinator.user_id, course_id=self.course.id))
            db.commit()
            self.course_id, self.course_code = self.course.id, self.course.programme_code
            self.subject_id, self.topic_id, self.subtopic_id = self.subject.id, self.topic.id, self.subtopic.id

    def headers(self, identity):
        return {"Authorization": "Bearer " + identity.token}

    def create_verified_source(self):
        created = client.post("/academic-content/sources", headers=self.headers(self.expert), json={
            "course_id": self.course_id, "subject_id": self.subject_id, "source_code": "RATIO-OFFICIAL",
            "title": "Verified Ratio Reference", "source_type": "TEXTBOOK", "issuing_authority": "SYS Faculty",
            "rights_classification": "REFERENCE_ONLY", "content_text": "Ratio compares two quantities using a common relationship.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        decision = client.post(f"/academic-content/sources/{created.json()['id']}/decision",
            headers=self.headers(self.admin), json={"action": "VERIFY", "comment": "Verified for the controlled benchmark."})
        self.assertEqual(decision.status_code, 200, decision.text)
        with database.SessionLocal() as db:
            revision_id = db.query(models.AcademicSourceRevision.id).filter_by(
                source_id=created.json()["id"], revision=1).scalar()
        return revision_id

    def knowledge_payload(self, revision_id):
        return {"topic_id": self.topic_id, "language": "en-IN",
            "objectives": ["Explain ratios and solve proportional comparisons."],
            "prerequisites": ["Basic multiplication and division"],
            "concepts": [{"name": "Ratio", "explanation": "Relative comparison"}],
            "definitions": [{"term": "Ratio", "definition": "Comparison of quantities"}],
            "formulas": [{"expression": "a:b", "spoken": "a is to b"}],
            "verified_facts": [],
            "worked_examples": [{"problem": "Compare 2 and 3", "answer": "2:3"}],
            "misconceptions": [{"mistake": "Adding unlike quantities", "correction": "Use comparable units"}],
            "exam_relevance": {"level": "foundational"}, "subtopic_coverage": [],
            "source_revision_ids": [revision_id]}

    def test_verified_sources_gate_knowledge_and_governance(self):
        revision_id = self.create_verified_source()
        created = client.post("/academic-content/knowledge-packages/revisions",
            headers=self.headers(self.expert), json=self.knowledge_payload(revision_id))
        self.assertEqual(created.status_code, 201, created.text)
        package_id = created.json()["id"]
        for identity, action, expected in ((self.expert, "SUBMIT", "SOURCE_REVIEW"),
                (self.expert, "EXPERT_VERIFY", "EXPERT_VERIFIED"), (self.admin, "APPROVE", "APPROVED")):
            response = client.post(f"/academic-content/knowledge-packages/{package_id}/decision",
                headers=self.headers(identity), json={"action": action, "comment": "Academic benchmark workflow decision."})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], expected)

    def test_unverified_source_and_unassigned_faculty_are_blocked(self):
        created = client.post("/academic-content/sources", headers=self.headers(self.expert), json={
            "course_id": self.course_id, "subject_id": self.subject_id, "source_code": "DRAFT",
            "title": "Draft source", "source_type": "FACULTY_NOTE", "content_text": "Unverified draft."})
        self.assertEqual(created.status_code, 201, created.text)
        with database.SessionLocal() as db:
            revision_id = db.query(models.AcademicSourceRevision.id).filter_by(source_id=created.json()["id"]).scalar()
        blocked = client.post("/academic-content/knowledge-packages/revisions",
            headers=self.headers(self.expert), json=self.knowledge_payload(revision_id))
        self.assertEqual(blocked.status_code, 422, blocked.text)
        denied = client.post("/academic-content/sources", headers=self.headers(self.reviewer), json={
            "course_id": self.course_id, "subject_id": self.subject_id, "source_code": "OUTSIDE",
            "title": "Outside responsibility", "source_type": "OTHER", "content_text": "Should be denied."})
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_professor_profile_and_reviewer_assignment(self):
        profile = client.put("/academic-content/professor-profiles", headers=self.headers(self.expert), json={
            "subject_id": self.subject_id, "language": "en-IN",
            "teaching_strategy": {"sequence": "concept-method-example-practice"},
            "required_stage_types": ["OBJECTIVES", "PREREQUISITES", "CONCEPT", "EXAMPLE", "RECAP"],
            "example_rules": ["Verify every calculation"], "narration_rules": ["Explain why every operation is used"],
            "visual_rules": ["Use ratio blocks where useful"], "assessment_rules": ["Include guided practice"],
            "accuracy_constraints": ["Recompute every numerical answer"]})
        self.assertEqual(profile.status_code, 200, profile.text)
        approved = client.post(f"/academic-content/professor-profiles/{profile.json()['id']}/approve",
            headers=self.headers(self.admin), json={"action": "VERIFY", "comment": "Approved arithmetic benchmark profile."})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        assignment = client.post("/academic-content/reviewers", headers=self.headers(self.admin),
            json={"topic_id": self.topic_id, "faculty_id": self.reviewer.user_id})
        self.assertEqual(assignment.status_code, 201, assignment.text)
        mine = client.get("/academic-content/reviewers/me", headers=self.headers(self.reviewer))
        self.assertEqual(mine.status_code, 200, mine.text)
        self.assertIn(self.topic_id, [item["topic_id"] for item in mine.json()["items"]])
        readiness = client.get(f"/academic-content/courses/{self.course_id}/benchmark-readiness",
            headers=self.headers(self.admin))
        self.assertEqual(readiness.status_code, 200, readiness.text)
        self.assertEqual(readiness.json()["subject_count"], 1)
        self.assertFalse(readiness.json()["ready"])

    def test_course_knowledge_studio_validation_and_admin_activation(self):
        policy = {"audience": "Competitive examination learners", "teaching_objective": "Build accurate conceptual mastery and exam application.",
            "default_language": "en-IN", "required_lesson_stages": ["INTRODUCTION", "CONCEPT", "EXAMPLE", "PRACTICE", "RECAP"],
            "delivery_requirements": ["Explain reasoning conversationally"], "accuracy_requirements": ["Use approved knowledge only"]}
        created = client.post(f"/academic-content/courses/{self.course_id}/teaching-pack/revisions",
            headers=self.headers(self.coordinator), json={"language": "en-IN", "course_policy": policy, "revision_notes": "Pilot policy"})
        self.assertEqual(created.status_code, 201, created.text)
        revision = created.json()["current_revision"]
        incomplete = client.post(f"/academic-content/courses/{self.course_id}/teaching-pack/revisions/{revision}/decision",
            headers=self.headers(self.coordinator), json={"action": "VALIDATE", "comment": "Validate initial teaching pack."})
        self.assertEqual(incomplete.status_code, 200, incomplete.text)
        self.assertEqual(incomplete.json()["revision"]["status"], "NEEDS_CORRECTION")
        profile = client.put("/academic-content/professor-profiles", headers=self.headers(self.coordinator), json={
            "subject_id": self.subject_id, "language": "en-IN", "teaching_strategy": {"sequence": "concept-example-practice-recap"},
            "required_stage_types": ["INTRODUCTION", "CONCEPT", "EXPLANATION", "EXAMPLE", "RECAP"],
            "example_rules": ["Show every step"], "narration_rules": ["Explain, do not merely read"],
            "visual_rules": ["Use worked boards"], "assessment_rules": ["Check understanding"],
            "accuracy_constraints": ["Recheck every answer"]})
        self.assertEqual(profile.status_code, 200, profile.text)
        denied = client.post(f"/academic-content/courses/{self.course_id}/teaching-pack/revisions/{revision}/decision",
            headers=self.headers(self.coordinator), json={"action": "ACTIVATE", "comment": "Attempt coordinator activation."})
        self.assertEqual(denied.status_code, 403, denied.text)
        activated = client.post(f"/academic-content/courses/{self.course_id}/teaching-pack/revisions/{revision}/decision",
            headers=self.headers(self.admin), json={"action": "ACTIVATE", "comment": "Administrator approved the governed teaching pack."})
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertEqual(activated.json()["status"], "ACTIVE")
        studio = client.get(f"/academic-content/courses/{self.course_id}/knowledge-studio", headers=self.headers(self.coordinator))
        self.assertEqual(studio.status_code, 200, studio.text)
        self.assertEqual(studio.json()["teaching_pack"]["active_revision"], revision)
        self.assertEqual(studio.json()["subjects"][0]["delivery_guide"]["status"], "APPROVED")

    def test_external_package_preview_and_governed_commit(self):
        payload = {"import_name": "Arithmetic pilot package", "source": {
            "source_code": f"EXT-{self.topic_id}", "title": "Verified external arithmetic reference",
            "source_type": "TEXTBOOK", "issuing_authority": "SYS Academic Team",
            "rights_classification": "REFERENCE_ONLY", "content_text": "Ratios compare quantities in the same units.",
            "verification_statement": "The administrator checked this source and confirms its academic provenance."},
            "packages": [{"topic_id": self.topic_id, "language": "en-IN",
                "objectives": ["Explain and apply ratios"], "prerequisites": ["Division"],
                "concepts": [{"name": "Ratio", "explanation": "A relative comparison of quantities"}],
                "definitions": [], "formulas": [], "verified_facts": [],
                "worked_examples": [{"problem": "Compare 2 and 3", "answer": "2:3",
                    "reasoning_steps": ["Write the quantities in the requested order."]}],
                "misconceptions": [{"mistake": "Reversing the terms", "correction": "Preserve the requested order."}],
                "exam_relevance": {"level": "foundational"},
                "subtopic_coverage": [{"subtopic_id": self.subtopic_id, "coverage": "Fully covered"}]}]}
        preview = client.post(f"/academic-content/courses/{self.course_id}/external-import/preview",
            headers=self.headers(self.admin), json=payload)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(preview.json()["valid"])
        committed = client.post(f"/academic-content/courses/{self.course_id}/external-import/commit",
            headers=self.headers(self.admin), json={**payload, "preview_hash": preview.json()["preview_hash"],
                "confirmation": "Approved for controlled academic review."})
        self.assertEqual(committed.status_code, 201, committed.text)
        self.assertEqual(committed.json()["imported"], 1)
        package = client.get(f"/academic-content/topics/{self.topic_id}/knowledge-package",
            headers=self.headers(self.admin))
        self.assertEqual(package.status_code, 200, package.text)
        self.assertEqual(package.json()["status"], "DRAFT")
        self.assertEqual(package.json()["revision"]["subtopic_coverage"][0]["subtopic_id"], self.subtopic_id)
        package_id = package.json()["id"]
        pilot_preview = client.get(f"/academic-content/courses/{self.course_id}/pilot-knowledge-approval-preview",
            headers=self.headers(self.admin))
        self.assertEqual(pilot_preview.status_code, 200, pilot_preview.text)
        self.assertEqual(pilot_preview.json()["eligible_count"], 1)
        pilot = client.post(f"/academic-content/courses/{self.course_id}/pilot-approve-knowledge",
            headers=self.headers(self.admin), json={"course_code": self.course_code,
                "reason": "Approved strictly for controlled pilot demonstration and later expert verification.",
                "expected_package_ids": [package_id]})
        self.assertEqual(pilot.status_code, 200, pilot.text)
        self.assertEqual(pilot.json()["status"], "PILOT_APPROVED")
        self.assertFalse(pilot.json()["institutional_approval"])
        assigned = client.post("/academic-content/reviewers", headers=self.headers(self.admin),
            json={"topic_id": self.topic_id, "faculty_id": self.reviewer.user_id})
        self.assertEqual(assigned.status_code, 201, assigned.text)
        for identity, action, expected in ((self.admin, "SUBMIT", "SOURCE_REVIEW"),
                (self.reviewer, "EXPERT_VERIFY", "EXPERT_VERIFIED"),
                (self.admin, "APPROVE", "APPROVED")):
            decision = client.post(f"/academic-content/knowledge-packages/{package_id}/decision",
                headers=self.headers(identity), json={"action": action, "comment": "Independent benchmark verification decision."})
            self.assertEqual(decision.status_code, 200, decision.text)
            self.assertEqual(decision.json()["status"], expected)
        workspace = client.get(f"/academic-content/courses/{self.course_id}/knowledge-review-workspace",
            headers=self.headers(self.admin))
        self.assertEqual(workspace.status_code, 200, workspace.text)
        self.assertTrue(workspace.json()["ready"])


if __name__ == "__main__":
    unittest.main()
