import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const ui = fs.readFileSync(new URL('../components/syllabus/SyllabusReviewWorkspace.js', import.meta.url), 'utf8');
const backend = fs.readFileSync(new URL('../../backend/app/routes/syllabus_review.py', import.meta.url), 'utf8');
test('blank and current syllabus downloads use distinct course filenames', () => {
  const expression = ui.match(/downloadBlob\(response.data, (`SYS_Syllabus_.*?`)\)/)?.[1];
  assert.ok(expression);
  const name = new Function('blank', 'courseId', 'review', `return ${expression}`);
  assert.equal(name(true, '2', {version:1}), 'SYS_Syllabus_Template_Course_2_v1.xlsx');
  assert.equal(name(false, '2', {version:3}), 'SYS_Syllabus_Current_Course_2_v3.xlsx');
});
test('UI and backend no longer expose the old review filename', () => {
  assert.doesNotMatch(ui, /SYS_Syllabus_Review_/);
  assert.doesNotMatch(backend, /SYS_Syllabus_Review_/);
  assert.ok(backend.includes('"Template" if blank else "Current"'));
});
