import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8');
const dashboard=read('../components/syllabus/SubjectReviewDashboard.js');
const actions=read('../components/syllabus/SyllabusDraftActions.js');
test('three pages retain authoring, upload, and review separation',()=>{
  const pages=read('../src/syllabusPages.js');assert.doesNotMatch(pages,/\["approved",/);
  assert.match(read('../components/syllabus/SyllabusReviewWorkspace.js'),/page==='approved'.*ApprovedRedirect/);
});
test('expert recommendations and final approval have distinct controls',()=>{
  for(const label of ['Request review','Recommend approval without changes','Submit proposed changes','Finally approve subject','Return for changes','Syllabus finally approved'])assert.ok(dashboard.includes(label));
  assert.match(dashboard,/task\.reviewer_id === data\?\.actor_id/);
  assert.match(dashboard,/data\.can_final_approve/);
});
test('administrator review readiness does not duplicate the syllabus structure tree',()=>{
  assert.match(dashboard,/!data\.can_manage\) && tree\(\)/);
  assert.match(dashboard,/t\?\.status === "RECOMMENDED"/);
  assert.match(dashboard,/Open expert recommendation/);
});
test('PDF downloads and reset require saved content',()=>{
  assert.match(dashboard,/Download complete syllabus PDF/);assert.match(dashboard,/Download subject PDF/);
  assert.match(actions,/disabled=\{disabled\|\|busy/);assert.match(actions,/course_code:code,reason,cancel_requests:cancel/);
  assert.match(actions,/Advanced actions/);assert.match(actions,/recovery snapshot/);
});
test('SYS branding, role-aware links, and history remain visible',()=>{
  assert.match(dashboard,/Shape Your Successful Future/);assert.match(dashboard,/courseHomeLink\(role, id\)/);
  assert.match(dashboard,/Approved version history and downloads/);assert.match(dashboard,/Review audit history/);
});
