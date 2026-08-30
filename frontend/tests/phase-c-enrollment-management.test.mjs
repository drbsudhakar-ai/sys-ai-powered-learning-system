import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("administrator cohort enrollment supports programme and present-year AND filtering", async () => {
  const route = await read("../../backend/app/routes/course_enrollments.py");
  const service = await read("../../backend/app/services/course_enrollments.py");
  assert.match(route, /enrollments\/preview/);
  assert.match(route, /enrollments\/bulk/);
  assert.match(service, /academic_program/);
  assert.match(service, /present_year/);
  assert.match(route, /Preview never creates enrollments|def preview/);
});

test("enrollment lifecycle, faculty scope, audit, and export are controlled", async () => {
  const route = await read("../../backend/app/routes/course_enrollments.py");
  const model = await read("../../backend/app/models.py");
  for (const state of ["ACTIVE", "COMPLETED", "WITHDRAWN", "SUSPENDED"]) assert.ok(route.includes(state));
  assert.match(route, /faculty_can_view/);
  assert.match(route, /AdminAuditLog/);
  assert.match(route, /export\.csv/);
  assert.match(model, /enrollment_source/);
  assert.match(model, /enrolled_by/);
});

test("professional administrator workspace previews before confirmation", async () => {
  const workspace = await read("../components/admin/CourseEnrollmentWorkspace.js");
  const api = await read("../src/api.js");
  assert.match(workspace, /Preview eligible students/);
  assert.match(workspace, /AND logic/);
  assert.match(workspace, /window\.confirm/);
  assert.match(workspace, /Export enrollments/);
  assert.match(api, /previewCourseEnrollmentCohort/);
  assert.match(api, /bulkEnrollCourseStudents/);
});

test("self-enrollment is an explicit per-course policy", async () => {
  const route = await read("../../backend/app/routes/courses.py");
  const model = await read("../../backend/app/models.py");
  assert.match(route, /if not course\.self_enrollment_enabled/);
  assert.match(model, /self_enrollment_enabled/);
});
