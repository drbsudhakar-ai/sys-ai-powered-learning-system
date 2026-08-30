import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../src/syllabusConfiguration.js', import.meta.url), 'utf8');
const { configuredOwnership, configurationLabel } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

test('saved subjects and assignments replace only their own administrative course rows', () => {
  const draft = { id: 1, syllabus_configuration: { subjects: [{ id: 'draft:1:new:a', course_id: 1 }], experts: [{ subject_id: 'draft:1:new:a', course_id: 1, faculty_id: 7 }] } };
  const result = configuredOwnership([draft], [{ id: 1, course_id: 1 }, { id: 2, course_id: 2 }], [{ course_id: 1 }, { course_id: 2 }]);
  assert.equal(result.subjects.length, 2);
  assert.equal(result.subjects[1].id, 'draft:1:new:a');
  assert.equal(result.experts[1].faculty_id, 7);
  assert.equal(result.experts[0].course_id, 2);
});
test('empty reset is not replaced by stale live administrative rows', () => {
  assert.deepEqual(configuredOwnership([{ id: 1, syllabus_configuration: {subjects: [], experts: []} }], [{course_id: 1}], [{course_id: 1}]), {subjects: [], experts: []});
});
test('working syllabus counts never imply publication', () => {
  assert.match(configurationLabel({status: 'WORKING_DRAFT', approved_subject_count: 0}), /0 subjects approved/);
  assert.match(configurationLabel({status: 'WORKING_DRAFT', approved_subject_count: 2}), /Approval and publication are separate/);
});
test('academic responsibilities uses saved draft identity and optimistic version', async () => {
  const text = await readFile(new URL('../components/admin/AcademicResponsibilitiesWorkspace.js', import.meta.url), 'utf8');
  assert.match(text, /configuredOwnership/);
  assert.match(text, /subject_key: subject.subject_key/);
  assert.match(text, /version: subject.draft_version/);
  assert.match(text, /action: "unassign"/);
});
test('review assignment shows a change action and pending registration guidance', async () => {
  const text = await readFile(new URL('../components/syllabus/SubjectReviewDashboard.js', import.meta.url), 'utf8');
  assert.match(text, /Change expert/);
  assert.match(text, /Registration pending/);
  assert.match(text, /data.faculty.map/);
});
