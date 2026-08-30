"""Administrative draft visibility without making draft content learnable."""
from tests import test_subject_syllabus_workflow as fixtures
from app import models
from app.services.syllabus_configuration import configuration
from app.routes.courses import _course_out


class SyllabusConfigurationTests(fixtures.SubjectWorkflowTests):
    def action(self, key, action, **extra):
        if action == 'unassign':
            return self.call('post', f'/reviews/{self.review["id"]}/subject-action', dict(
                subject_key=key, action=action, version=self.dashboard()['version'], **extra))
        return super().action(key, action, **extra)

    def test_saved_subjects_and_assignments_share_configuration(self):
        before = self.client.get(f'/courses/{self.course.id}').json()
        self.assertEqual(before['subject_count'], 2)
        self.assertEqual(before['unit_count'], 2)
        self.assertEqual(before['syllabus_configuration']['approved_subject_count'], 0)
        self.action('new:b', 'assign', reviewer_id=self.expert.id)
        result = self.client.get(f'/courses/{self.course.id}').json()
        self.assertEqual(result['subject_expert_count'], 1)
        expert = result['syllabus_configuration']['experts'][0]
        self.assertEqual(expert['subject_name'], 'English')
        self.assertEqual(expert['faculty_id'], self.expert.id)
        self.assertEqual(result['syllabus_configuration']['status'], 'WORKING_DRAFT')
        self.assertEqual(self.db.query(models.Subject).count(), 0)
        self.assertEqual(self.course.syllabus_revision, 0)

    def test_pending_registration_can_be_assigned_but_not_requested(self):
        self.other.account_status = 'PENDING_ACTIVATION'
        self.db.commit()
        faculty = self.call('get', '/subject-dashboard').json()['faculty']
        self.assertIn(self.other.id, [f['id'] for f in faculty])
        self.action('new:a', 'assign', reviewer_id=self.other.id)
        board = self.dashboard()
        self.assertFalse(board['tasks'][0]['assignment_valid'])
        self.call('post', f'/reviews/{self.review["id"]}/subject-action', dict(
            action='request', subject_key='new:a', version=board['version']), code=422)
        self.other.account_status = 'ACTIVE'; self.db.commit()
        self.action('new:a', 'request')

    def test_disabled_and_inactive_employment_are_excluded(self):
        self.other.employment_status = 'INACTIVE'; self.db.commit()
        self.assertNotIn(self.other.id, [f['id'] for f in self.call('get', '/subject-dashboard').json()['faculty']])
        self.call('post', f'/reviews/{self.review["id"]}/subject-action', dict(
            action='assign', subject_key='new:a', version=self.review['version'], reviewer_id=self.other.id), code=422)

    def test_unassign_reassign_is_version_guarded(self):
        self.action('new:a', 'assign', reviewer_id=self.expert.id)
        self.action('new:a', 'unassign')
        self.assertEqual(configuration(self.db, self.course)['experts'], [])
        self.action('new:a', 'assign', reviewer_id=self.other.id)
        self.assertEqual(configuration(self.db, self.course)['experts'][0]['faculty_id'], self.other.id)
        self.action('new:a', 'request')
        board = self.dashboard()
        self.call('post', f'/reviews/{self.review["id"]}/subject-action', dict(
            action='unassign', subject_key='new:a', version=board['version']), code=409)

    def test_manager_only_draft_configuration(self):
        self.assertIsNone(_course_out(self.course, self.db, self.other).syllabus_configuration)
        self.assertIsNotNone(_course_out(self.course, self.db, self.cc).syllabus_configuration)
        student = models.User(name='Student', role='student', roll_number='TEST-STUDENT', is_active=True, account_status='ACTIVE')
        self.db.add(student); self.db.commit()
        self.assertIsNone(_course_out(self.course, self.db, student).syllabus_configuration)
        self.actor = student
        self.assertEqual(self.client.get(f'/courses/{self.course.id}').status_code, 404)
        self.call('get', '/subject-dashboard', code=403)

    def test_reset_removes_projected_counts_and_assignment(self):
        self.action('new:a', 'assign', reviewer_id=self.expert.id)
        self.reload()
        self.call('post', f'/reviews/{self.review["id"]}/reset', dict(
            version=self.review['version'], course_code=self.course.programme_code,
            reason='Wrong workbook uploaded', cancel_requests=True))
        result = configuration(self.db, self.course)
        self.assertEqual(result['subject_count'], 0)
        self.assertEqual(result['experts'], [])

    def test_existing_subject_assignment_is_shared_with_academic_responsibilities(self):
        course = models.Course(title='Existing structure', created_by=self.admin.id,
                               publication_status='DRAFT', is_active=False)
        self.db.add(course); self.db.flush()
        subject = models.Subject(course_id=course.id, name='Physics')
        self.db.add(subject); self.db.commit()
        self.course = course; self.root = f'/courses/{course.id}/syllabus-review'
        self.review = self.call('post', '/reviews', {}).json()
        self.action(f'subject:{subject.id}', 'assign', reviewer_id=self.expert.id)
        assignment = self.db.query(models.SubjectExpertAssignment).filter_by(subject_id=subject.id).one()
        self.assertEqual(assignment.faculty_id, self.expert.id)
        self.assertEqual(configuration(self.db, course)['experts'][0]['faculty_id'], self.expert.id)

    def test_course_profile_pdf_uses_saved_configuration(self):
        from io import BytesIO
        from pypdf import PdfReader
        self.action('new:b', 'assign', reviewer_id=self.expert.id)
        response = self.client.get(f'/admin/courses/{self.course.id}/profile.pdf')
        self.assertEqual(response.status_code, 200, response.text[:200] if response.status_code != 200 else '')
        text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('SAVED WORKING SYLLABUS', text)
        self.assertIn('0 of 2 subjects approved', ' '.join(text.split()))
        self.assertIn('English', text)
        self.assertIn(self.expert.name, text)
