import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('enrollment programme dropdown loads master options and invalidates old previews', async () => {
  const source = await readFile(new URL('../components/admin/CourseEnrollmentWorkspace.js', import.meta.url), 'utf8');
  assert.match(source, /Academic programme<select/);
  assert.match(source, /getEnrollmentProgrammes\(id\)/);
  assert.match(source, /All academic programmes/);
  assert.match(source, /programmes\.map/);
  assert.match(source, /function changeFilter[^\n]*setPreview\(null\); setSelected\(\[\]\)/);
  assert.match(source, /!filters.academic_program && !filters.present_year/);
});

test('programme options are administrator-only and drawn from student master', async () => {
  const source = await readFile(new URL('../../backend/app/routes/course_enrollments.py', import.meta.url), 'utf8');
  const endpoint = source.slice(source.indexOf('def academic_programmes('), source.indexOf('@router.post("/{course_id}/enrollments/preview")'));
  assert.match(endpoint, /Depends\(_admin\)/);
  assert.match(endpoint, /models.User.role == "student"/);
  assert.match(endpoint, /distinct\(\)/);
  assert.match(endpoint, /value.strip\(\)/);
  assert.match(endpoint, /sorted\(/);
});
