import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const read = (path) => readFile(new URL(path, import.meta.url), 'utf8');

test('My Courses separates locked assignments from the published catalog', async () => {
  const source = await read('../components/auth/StudentCoursesWorkspace.js');
  assert.match(source, /course.can_access \?/);
  assert.match(source, /Locked ·/);
  assert.match(source, /course.lock_reason/);
  assert.match(source, /Published course catalog/);
  assert.match(source, /course.self_enrollment_enabled \?/);
  assert.match(source, /Continue learning/);
});

test('syllabus exposes actual progress, scoped weights and subtopic views', async () => {
  const source = await read('../pages/courses/[id]/workspace.js');
  assert.match(source, /topic_states/);
  assert.match(source, /subtopic_states/);
  assert.match(source, /Configured weightage/);
  assert.match(source, /Weightage not configured/);
  assert.match(source, /scope="unit"/);
  assert.match(source, /subtopic.description/);
  assert.match(source, /onLaunch\(topic, subtopic.id\)/);
  assert.match(source, /continue_learning.classroom_path/);
});

test('existing global role shell remains the single owner of navigation', async () => {
  const layout = await read('../components/Layout.js');
  const cards = await read('../components/auth/StudentCoursesWorkspace.js');
  assert.match(layout, /<RoleWorkspaceShell/);
  assert.doesNotMatch(cards, /<RoleWorkspaceShell|<Layout/);
});
