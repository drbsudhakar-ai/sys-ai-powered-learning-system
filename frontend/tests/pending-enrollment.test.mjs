import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('draft assignments have pending labels and publication confirmation carries count', async () => {
  const workspace = await readFile(new URL('../components/admin/CourseEnrollmentWorkspace.js', import.meta.url), 'utf8');
  const profile = await readFile(new URL('../components/admin/CourseProfilePage.js', import.meta.url), 'utf8');
  assert.match(workspace, /Pending activation/);
  assert.match(workspace, /published \? "Enroll" : "Assign"/);
  assert.match(workspace, /!assignable/);
  assert.match(workspace, /Pending assignments do not grant learning access/);
  assert.match(profile, /pending_enrollment_count/);
  assert.match(profile, /activate_pending: true, expected_pending_count: pendingCount/);
  assert.match(profile, /enrollment_activation\?\.skipped/);
});
