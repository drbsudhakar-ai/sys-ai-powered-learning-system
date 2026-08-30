"""Isolated API tests for requested subject review and exact-version PDFs."""
import copy
import unittest
from io import BytesIO
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pypdf import PdfReader
from app import models, database
from app.main import app
from app.routes.auth import get_current_user
from app.services import syllabus_subjects as service

class SubjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.admin=models.User(name='SYS Administrator',email='admin@example.org',role='admin',is_active=True,account_status='ACTIVE')
        self.cc=models.User(name='Course Coordinator',email='cc@example.org',role='faculty',employee_code='CC',is_active=True,account_status='ACTIVE')
        self.expert=models.User(name='Subject Expert',email='expert@example.org',role='faculty',employee_code='EX',is_active=True,account_status='ACTIVE')
        self.other=models.User(name='Other Faculty',email='other@example.org',role='faculty',employee_code='OTHER',is_active=True,account_status='ACTIVE')
        self.db.add_all([self.admin,self.cc,self.expert,self.other]);self.db.flush()
        self.course=models.Course(title='Telangana Police Constable Pilot',programme_code='TGPCPWT-2026',created_by=self.admin.id,publication_status='DRAFT',is_active=False)
        self.db.add(self.course);self.db.flush();self.db.add(models.FacultyCourseAssignment(course_id=self.course.id,faculty_id=self.cc.id));self.db.commit()
        self.actor=self.admin
        def session_dependency():
            try: yield self.db
            except Exception:
                self.db.rollback()
                raise
        app.dependency_overrides[database.get_db]=session_dependency
        app.dependency_overrides[get_current_user]=lambda:self.actor
        self.dispatch=patch('app.routes.syllabus_subjects.dispatch_later');self.dispatch.start()
        self.legacy_dispatch=patch('app.routes.syllabus_review.dispatch_later');self.legacy_dispatch.start()
        self.client=TestClient(app);self.root=f'/courses/{self.course.id}/syllabus-review'
        r=self.call('post','/reviews',{});self.review=r.json()
        self.nodes=[]
        for x,name in [('a','Arithmetic'),('b','English')]:
            for level,key,parent,n in [('subject',x,None,name),('unit',x+'u','new:'+x,'Fundamentals'),('topic',x+'t','new:'+x+'u','Introduction')]:
                self.nodes.append(dict(key='new:'+key,level=level,parent=parent,name=n,description='Pilot description',learning_outcome='',sequence=1 if x=='a' or level!='subject' else 2))
        self.save(self.nodes)

    def tearDown(self):
        app.dependency_overrides.clear();self.dispatch.stop();self.legacy_dispatch.stop();self.db.close();self.engine.dispose()

    def call(self,method,path,body=None,code=200):
        r=getattr(self.client,method)(self.root+path,**({'json':body} if body is not None else {}))
        if path=='/reviews' and code==200: code=201
        self.assertEqual(r.status_code,code,r.text[:1500]);return r

    def reload(self):
        self.review=self.call('get',f'/reviews/{self.review["id"]}').json()

    def save(self,nodes):
        self.review=self.call('put',f'/reviews/{self.review["id"]}',dict(version=self.review['version'],nodes=nodes,summary='Pilot syllabus')).json()

    def dashboard(self):
        return self.call('get','/subject-dashboard').json()['reviews'][0]

    def action(self,key,action,**extra):
        board=self.dashboard();task=next((t for t in board['tasks'] if t['subject_key']==key),None)
        version=board['version'] if action in {'assign','request'} else task['version']
        return self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key=key,action=action,version=version,**extra))

    def request_review(self,key='new:a'):
        self.actor=self.cc;self.action(key,'assign',reviewer_id=self.expert.id);self.action(key,'request')

    def recommend(self,key='new:a',nodes=None):
        self.actor=self.expert;self.action(key,'recommend',comment='Academically verified',**({'nodes':nodes} if nodes is not None else {}))

    def approve(self,key='new:a'):
        self.actor=self.admin;self.action(key,'approve',comment='Verified and finally approved')

    def test_assignment_required_and_scoped(self):
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='request',version=self.review['version']),code=422)
        self.db.rollback();self.request_review()
        self.actor=self.expert;board=self.dashboard();self.assertEqual([n['name'] for n in board['subjects']],['Arithmetic'])
        self.call('get',f'/reviews/{self.review["id"]}/syllabus.pdf',code=403)
        self.call('get',f'/reviews/{self.review["id"]}/syllabus.pdf?subject_key=new:b',code=403)
        self.actor=self.other;self.call('get','/subject-dashboard',code=403)

    def test_dual_role_faculty_dashboard_and_workspace_include_saved_draft(self):
        self.actor=self.cc
        self.action('new:a','assign',reviewer_id=self.cc.id)
        self.action('new:b','assign',reviewer_id=self.cc.id)

        dashboard=self.client.get('/auth/dashboard').json()
        self.assertEqual(dashboard['summary']['assigned_courses'],1)
        self.assertEqual(dashboard['summary']['assigned_subjects'],2)
        self.assertEqual({item['name'] for item in dashboard['subjects']},{'Arithmetic','English'})
        self.assertTrue(all(item['review_id'] == self.review['id'] and item['review_task_id'] for item in dashboard['subjects']))

        response=self.client.get(f'/courses/{self.course.id}/workspace')
        self.assertEqual(response.status_code,200,response.text)
        workspace=response.json()
        self.assertTrue(workspace['syllabus_status']['is_draft'])
        self.assertEqual(workspace['course']['subject_count'],2)
        self.assertEqual(workspace['course']['unit_count'],2)
        self.assertEqual({item['name'] for item in workspace['syllabus']},{'Arithmetic','English'})
        self.assertTrue(all(item['assigned_to_actor'] and item['review_task_id'] for item in workspace['syllabus']))

    def test_recommend_approve_and_materialize_only_when_all_approved(self):
        self.request_review();self.recommend();self.approve()
        self.assertEqual(self.db.query(models.Subject).count(),0)
        self.request_review('new:b');self.recommend('new:b');self.approve('new:b')
        self.assertEqual(self.db.query(models.Subject).count(),2)
        self.assertEqual(self.db.query(models.SubjectExpertAssignment).count(),2)
        self.db.refresh(self.course);self.assertEqual(self.course.syllabus_revision,1)
        self.assertEqual(self.course.publication_status,'DRAFT')

    def test_existing_syllabus_approvals_remain_valid_while_weightages_follow_separate_governance(self):
        self.request_review();self.recommend();self.approve()
        self.request_review('new:b');self.recommend('new:b');self.approve('new:b')
        subjects=self.db.query(models.Subject).order_by(models.Subject.id).all()
        for subject in subjects:
            self.db.add(models.SubjectWeightage(course_id=self.course.id,subject_id=subject.id,weight_percent=50))
            self.db.add(models.UnitWeightage(subject_id=subject.id,unit_id=subject.units[0].id,weight_percent=100))
            self.db.add(models.TopicWeightage(subject_id=subject.id,topic_id=subject.topics[0].id,weight_percent=100))
        self.db.commit()
        self.actor=self.cc
        response=self.client.post(f'/admin/courses/{self.course.id}/coordinator-readiness',json={'action':'confirm','comment':'Complete course checked'})
        self.assertEqual(response.status_code,409,response.text)
        for subject in subjects:
            self.actor=self.expert
            tree=self.client.get(f'/admin/courses/{self.course.id}/weightages').json()
            governance=next(item['governance'] for item in tree['subjects'] if item['id']==subject.id)
            response=self.client.post(f'/admin/courses/{self.course.id}/weightages/{subject.id}/governance',json={
                'action':'recommend','version':governance['version'],'comment':'All academic groups verified'})
            self.assertEqual(response.status_code,200,response.text)
        self.actor=self.cc
        response=self.client.post(f'/admin/courses/{self.course.id}/coordinator-readiness',json={'action':'confirm','comment':'Complete course checked'})
        self.assertEqual(response.status_code,200,response.text)
        self.actor=self.admin
        response=self.client.post(f'/admin/courses/{self.course.id}/approve-all-eligible-subjects',json={'comment':'Institutional approval'})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['approved_count'],2)
        self.assertTrue(all(row.status=='APPROVED' for row in self.db.query(models.SubjectWeightageApproval)))
        self.assertTrue(all(task.status=='APPROVED' for task in self.db.query(models.SyllabusSubjectReview)))

    def test_controlled_pilot_uses_draft_subjects_without_fake_syllabus_approvals(self):
        self.request_review('new:a');self.recommend('new:a');self.approve('new:a')
        self.actor=self.admin
        response=self.client.post(f'/admin/courses/{self.course.id}/pilot-governance',json={
            'action':'enable','course_code':'TGPCPWT-2026','reason':'Validate AI lecturer before institutional demonstration'})
        self.assertEqual(response.status_code,200,response.text)

        tree=self.client.get(f'/admin/courses/{self.course.id}/weightages').json()
        self.assertTrue(tree['pilot']);self.assertEqual(len(tree['subjects']),2)
        self.assertEqual({item['syllabus_status'] for item in tree['subjects']},{'APPROVED','NOT_REQUESTED'})
        response=self.client.put(f'/admin/courses/{self.course.id}/pilot-weightages',json={
            'level':'subject','parent_key':f'course:{self.course.id}','items':[
                {'item_key':'new:a','weight_percent':50},{'item_key':'new:b','weight_percent':50}]})
        self.assertEqual(response.status_code,200,response.text)

        task=self.db.query(models.SyllabusSubjectReview).filter_by(review_id=self.review['id'],subject_key='new:a').one()
        self.actor=self.expert
        for level,parent,item in [('unit','new:a','new:au'),('topic','new:au','new:at')]:
            response=self.client.put(f'/admin/courses/{self.course.id}/pilot-weightages',json={
                'level':level,'parent_key':parent,'items':[{'item_key':item,'weight_percent':100}]})
            self.assertEqual(response.status_code,200,response.text)
        tree=self.client.get(f'/admin/courses/{self.course.id}/weightages').json()
        self.assertEqual([item['id'] for item in tree['subjects']],['new:a'])
        subject=next(item for item in tree['subjects'] if item['id']=='new:a')
        self.assertTrue(subject['governance']['complete'])
        scoped=self.client.get(f'/admin/courses/{self.course.id}/weightages?review_task_id={task.id}')
        self.assertEqual(scoped.status_code,200,scoped.text)
        self.assertEqual([item['id'] for item in scoped.json()['subjects']],['new:a'])
        dedicated=self.client.get(f'/admin/courses/{self.course.id}/subject-expert-weightages/{task.id}')
        self.assertEqual(dedicated.status_code,200,dedicated.text)
        self.assertEqual([item['id'] for item in dedicated.json()['subjects']],['new:a'])
        self.actor=self.cc
        coordinator=self.client.get(f'/admin/courses/{self.course.id}/coordinator-weightages')
        self.assertEqual(coordinator.status_code,200,coordinator.text)
        self.assertEqual(len(coordinator.json()['subjects']),2)
        self.actor=self.expert
        response=self.client.post(f'/admin/courses/{self.course.id}/pilot-weightages/{task.id}/governance',json={
            'action':'recommend','version':subject['governance']['version'],'comment':'Pilot hierarchy and percentages verified'})
        self.assertEqual(response.status_code,200,response.text)
        self.actor=self.admin
        response=self.client.post(f'/admin/courses/{self.course.id}/pilot-weightages/{task.id}/governance',json={
            'action':'approve','version':response.json()['version'],'comment':'Approved only for controlled pilot testing'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'PILOT_APPROVED')
        self.assertEqual(self.db.query(models.Subject).count(),0)
        tree=self.client.get(f'/admin/courses/{self.course.id}/weightages').json()
        pending=next(item for item in tree['subjects'] if item['id']=='new:b')
        self.assertEqual(pending['syllabus_status'],'NOT_REQUESTED')

    def test_legacy_approval_bypass_is_blocked(self):
        self.call('post',f'/reviews/{self.review["id"]}/action',dict(version=self.review['version'],action='approve',comment='bypass'),code=409)

    def test_expert_changes_cannot_change_units(self):
        self.request_review();self.actor=self.expert;t=self.dashboard()['tasks'][0]
        nodes=copy.deepcopy(t['source_nodes']);next(n for n in nodes if n['level']=='unit')['name']='Unauthorized'
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='recommend',version=t['version'],nodes=nodes,comment='Changed'),code=422)

    def test_changed_branch_invalidates_only_its_review(self):
        self.request_review();self.request_review('new:b');self.actor=self.cc;self.reload()
        nodes=copy.deepcopy(self.review['nodes']);nodes[2]['description']='Changed content';self.save(nodes)
        statuses={t['subject_key']:t['status'] for t in self.dashboard()['tasks']}
        self.assertEqual(statuses,{'new:a':'NOT_REQUESTED','new:b':'IN_REVIEW'})

    def test_reset_requires_cancellation_and_retains_snapshot(self):
        self.request_review();self.actor=self.cc;self.reload()
        body=dict(version=self.review['version'],course_code='TGPCPWT-2026',reason='Wrong workbook uploaded')
        self.call('post',f'/reviews/{self.review["id"]}/reset',body,code=409);self.db.rollback()
        body['cancel_requests']=True
        self.review=self.call('post',f'/reviews/{self.review["id"]}/reset',body).json();self.assertEqual(self.review['nodes'],[])
        log=self.db.query(models.AdminAuditLog).filter_by(action='syllabus.reset_snapshot').one();self.assertEqual(len(log.details['nodes']),6)

    def test_reset_blocked_after_one_final_approval(self):
        self.request_review();self.recommend();self.approve();self.reload()
        self.call('post',f'/reviews/{self.review["id"]}/reset',dict(version=self.review['version'],course_code='TGPCPWT-2026',reason='Wrong upload',cancel_requests=True),code=409)

    def test_pdf_is_branded_and_not_mislabelled_approved(self):
        response=self.call('get',f'/reviews/{self.review["id"]}/syllabus.pdf')
        text=''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('DRAFT - NOT APPROVED',text);self.assertIn('Strengthen Your Skills',text)
        self.request_review();self.recommend();self.approve()
        response=self.call('get',f'/reviews/{self.review["id"]}/syllabus.pdf')
        text=''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('PARTIALLY APPROVED - NOT PUBLISHED',text)

    def test_unapproved_publication_readiness_false(self):
        self.assertFalse(service.publication_ready(self.db,self.course))

    def test_subject_changes_are_proposals_until_final_decision(self):
        self.request_review();self.actor=self.expert;t=self.dashboard()['tasks'][0]
        desired=copy.deepcopy(t['source_nodes']);desired[-1]['description']='Expert suggested explanation'
        self.recommend(nodes=desired)
        self.actor=self.admin;self.reload();self.assertNotEqual(self.review['nodes'][2]['description'],'Expert suggested explanation')
        self.approve();self.reload();self.assertIn('Expert suggested explanation',[n['description'] for n in self.review['nodes']])

    def test_notifications_target_expert_and_coordinator(self):
        self.request_review();note=self.db.query(models.Notification).order_by(models.Notification.id.desc()).first()
        self.assertIn('/syllabus/reviews?review=',note.link_path)
        recipients={x.user_id for x in self.db.query(models.NotificationDelivery).filter_by(notification_id=note.id)}
        self.assertEqual(recipients,{self.expert.id})
        self.recommend();note=self.db.query(models.Notification).order_by(models.Notification.id.desc()).first()
        recipients={x.user_id for x in self.db.query(models.NotificationDelivery).filter_by(notification_id=note.id)}
        self.assertIn(self.cc.id,recipients);self.assertNotIn(self.other.id,recipients)

    def test_return_then_resubmit_and_stale_version(self):
        self.request_review();self.recommend();self.actor=self.cc
        self.action('new:a','return',comment='Please add an example')
        self.actor=self.expert;t=self.dashboard()['tasks'][0]
        self.assertEqual(t['status'],'RETURNED')
        self.action('new:a','save',comment='Example checked')
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='recommend',version=t['version'],comment='Stale request'),code=409)

    def test_published_course_keeps_live_syllabus_until_publish(self):
        self.request_review();self.recommend();self.approve();self.request_review('new:b');self.recommend('new:b');self.approve('new:b')
        self.course.publication_status='PUBLISHED';self.course.is_active=True;self.db.commit()
        self.actor=self.cc;self.review=self.call('post','/reviews',{}).json()
        desired=copy.deepcopy(self.review['nodes']);desired[-1]['description']='New published revision candidate';self.save(desired)
        for n in [x for x in desired if x['level']=='subject']:
            task=next(t for t in self.dashboard()['tasks'] if t['subject_key']==n['key'])
            if task['status']!='APPROVED':
                self.request_review(n['key']);self.recommend(n['key']);self.approve(n['key'])
        self.assertNotIn('New published revision candidate',[t.description for t in self.db.query(models.Topic)])
        service.finalize_for_publication(self.db,self.admin,self.course);self.db.commit()
        self.assertIn('New published revision candidate',[t.description for t in self.db.query(models.Topic)])

    def test_student_cannot_download_unpublished_version(self):
        self.request_review();self.recommend();self.approve();self.request_review('new:b');self.recommend('new:b');self.approve('new:b')
        student=models.User(name='Student',role='student',roll_number='TEST-1',is_active=True,account_status='ACTIVE')
        self.db.add(student);self.db.flush();self.db.add(models.StudentCourseEnrollment(course_id=self.course.id,student_id=student.id,status='ACTIVE'))
        self.course.publication_status='PUBLISHED';self.course.is_active=True;self.db.commit();self.actor=student
        self.call('get','/approved.pdf',code=403)

    def test_expert_cannot_reset(self):
        self.request_review();self.actor=self.expert
        self.call('post',f'/reviews/{self.review["id"]}/reset',dict(version=1,course_code='TGPCPWT-2026',reason='Wrong workbook',cancel_requests=True),code=403)

    def test_notification_failure_rolls_back_request(self):
        self.actor=self.cc;self.action('new:a','assign',reviewer_id=self.expert.id)
        with patch('app.services.syllabus_subjects.notify',side_effect=RuntimeError('outbox failure')):
            with self.assertRaises(RuntimeError):self.action('new:a','request')
        self.assertEqual(self.dashboard()['tasks'][0]['status'],'NOT_REQUESTED')

    def test_reviewer_cannot_final_approve_own_recommendation(self):
        self.request_review();self.recommend()
        self.db.add(models.FacultyCourseAssignment(course_id=self.course.id,faculty_id=self.expert.id));self.db.commit()
        t=self.dashboard()['tasks'][0]
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='approve',version=t['version'],comment='Self approval'),code=403)

    def test_course_coordinator_can_return_but_cannot_finally_approve(self):
        self.request_review();self.recommend();self.actor=self.cc
        task=self.dashboard()['tasks'][0]
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='approve',version=task['version'],comment='Coordinator approval'),code=403)
        self.db.rollback();task=self.dashboard()['tasks'][0]
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='return',version=task['version'],comment='Add academic detail'))

    def test_archived_course_blocks_requests(self):
        self.course.publication_status='ARCHIVED';self.db.commit()
        self.call('post',f'/reviews/{self.review["id"]}/subject-action',dict(subject_key='new:a',action='assign',version=self.review['version'],reviewer_id=self.expert.id),code=409)

    def test_p029_migration_retains_existing_syllabus(self):
        import importlib.util
        from pathlib import Path
        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec=importlib.util.spec_from_file_location('p029',Path(__file__).resolve().parents[1]/'alembic/versions/20260828_p029_subject_review.py')
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        engine=sa.create_engine('sqlite://')
        with engine.begin() as conn:
            conn.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY)'))
            conn.execute(sa.text('CREATE TABLE subjects (id INTEGER PRIMARY KEY)'))
            conn.execute(sa.text('CREATE TABLE courses (id INTEGER PRIMARY KEY, published_at DATETIME, publication_status TEXT, syllabus_revision INTEGER)'))
            conn.execute(sa.text('CREATE TABLE syllabus_reviews (id INTEGER PRIMARY KEY, subject_id INTEGER, status TEXT, proposed_nodes TEXT)'))
            conn.execute(sa.text('CREATE TABLE syllabus_revisions (id INTEGER PRIMARY KEY, course_id INTEGER, number INTEGER, created_at DATETIME, nodes TEXT)'))
            conn.execute(sa.text("INSERT INTO courses VALUES (1,'2026-08-28','PUBLISHED',1)"))
            conn.execute(sa.text("INSERT INTO syllabus_reviews VALUES (1,NULL,'SUBMITTED','saved syllabus')"))
            conn.execute(sa.text("INSERT INTO syllabus_revisions VALUES (1,1,1,'2026-08-27','immutable syllabus')"))
            with Operations.context(MigrationContext.configure(conn)):migration.upgrade()
            self.assertEqual(conn.execute(sa.text('SELECT proposed_nodes FROM syllabus_reviews')).scalar(),'saved syllabus')
            self.assertEqual(conn.execute(sa.text('SELECT status FROM syllabus_reviews')).scalar(),'DRAFT')
            self.assertEqual(conn.execute(sa.text('SELECT nodes FROM syllabus_revisions')).scalar(),'immutable syllabus')
            self.assertIsNotNone(conn.execute(sa.text('SELECT published_at FROM syllabus_revisions')).scalar())
        engine.dispose()
