import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const form = await readFile(new URL('../components/admin/CourseRecordFormPage.js', import.meta.url), 'utf8');
const css = await readFile(new URL('../components/admin/CourseMasterWorkspace.module.css', import.meta.url), 'utf8');

test('self-enrollment has one accessible label and associated guidance', () => {
  assert.match(form, /className=\{styles.enrollmentToggle\} htmlFor="self_enrollment_enabled"/);
  assert.match(form, /aria-describedby="self-enrollment-help"/);
  assert.match(form, /id="self-enrollment-help"/);
  assert.doesNotMatch(form, /<Field id="self_enrollment_enabled"/);
});

test('checkbox has compact dimensions, aligned label and keyboard focus', () => {
  assert.match(css, /\.enrollmentToggle\{display:flex;align-items:center;gap:10px/);
  const rule = css.match(/\.enrollmentToggle input\[type="checkbox"\]\{([^}]+)\}/)?.[1];
  assert.ok(rule);
  for (const declaration of ['width:18px;', 'height:18px;', 'min-height:18px;', 'padding:0;', 'margin:0;', 'flex:0 0 18px;']) assert.ok(rule.includes(declaration));
  assert.match(css, /\.enrollmentToggle input\[type="checkbox"\]:focus-visible/);
});

test('boolean toggle and default-off policy remain unchanged', () => {
  assert.match(form, /self_enrollment_enabled: false/);
  assert.match(form, /type === "checkbox" \? checked/);
  assert.match(form, /checked=\{Boolean\(form.self_enrollment_enabled\)\} onChange=\{change\}/);
  assert.match(form, /self_enrollment_enabled: Boolean\(form.self_enrollment_enabled\)/);
});
