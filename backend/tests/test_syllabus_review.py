"""Workbook/identity regressions; lifecycle tests now live in test_subject_syllabus_workflow."""
import copy
import unittest
from io import BytesIO
from zipfile import ZipFile
from app import models
from app.services.syllabus_workbook import contract
from tests import test_subject_syllabus_workflow as fixtures

class WorkbookCompatibilityTests(unittest.TestCase):
    setUp = fixtures.SubjectWorkflowTests.setUp
    tearDown = fixtures.SubjectWorkflowTests.tearDown
    call = fixtures.SubjectWorkflowTests.call
    save = fixtures.SubjectWorkflowTests.save

    def test_workbook_branding_hidden_identifiers_and_dropdowns(self):
        response=self.call('get',f'/reviews/{self.review["id"]}/workbook.xlsx')
        with ZipFile(BytesIO(response.content)) as book:
            self.assertIn('SYS Metadata',book.read('xl/workbook.xml').decode())
            self.assertIn('Strengthen Your Skills',book.read('xl/worksheets/sheet1.xml').decode())
            self.assertIn('dataValidation',book.read('xl/worksheets/sheet3.xml').decode())
            self.assertIn('hidden="1"',book.read('xl/worksheets/sheet3.xml').decode())

    def test_roundtrip_rename_does_not_apply_before_save(self):
        row=self.db.get(models.SyllabusReview,self.review['id']);body=contract(row)
        body['sheets']['Subjects'][0]['Name']='Renamed Arithmetic'
        r=self.call('post',f'/reviews/{row.id}/workbook-preview',{**body,'version':row.version})
        self.assertIn('Renamed Arithmetic',[n['name'] for n in r.json()['nodes']])
        self.assertNotIn('Renamed Arithmetic',[n['name'] for n in row.proposed_nodes])

    def test_stale_metadata_and_damaged_identifiers_rejected(self):
        row=self.db.get(models.SyllabusReview,self.review['id']);body=contract(row)
        bad=copy.deepcopy(body);bad['sheets']['Topics'][0]['SYS Reference']+='broken'
        self.call('post',f'/reviews/{row.id}/workbook-preview',{**bad,'version':row.version},code=422)
        body['metadata']['Review']='9999'
        self.call('post',f'/reviews/{row.id}/workbook-preview',{**body,'version':row.version},code=409)

    def test_unknown_revision_does_not_fall_back(self):
        self.call('get','/approved.pdf?revision=999',code=409)

    def test_coordinator_can_edit_admin_working_syllabus(self):
        self.actor=self.cc;nodes=copy.deepcopy(self.review['nodes']);nodes[0]['description']='Coordinator saved this'
        self.save(nodes);self.assertEqual(self.review['nodes'][0]['description'],'Coordinator saved this')

    def test_missing_parent_and_duplicate_order_rejected(self):
        for mode in ['parent','order']:
            nodes=copy.deepcopy(self.review['nodes'])
            if mode=='parent':nodes[-1]['parent']='new:missing'
            else:nodes[-1]['sequence']=1;nodes.append({**nodes[-1],'key':'new:other','name':'Another topic'})
            self.call('put',f'/reviews/{self.review["id"]}',dict(version=self.review['version'],nodes=nodes,summary='Invalid structure'),code=422)
