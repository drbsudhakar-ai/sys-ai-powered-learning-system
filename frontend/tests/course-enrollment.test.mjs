import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("published course enrollment endpoint requires the student role", async () => {
  const routes = await read("../../backend/app/routes/courses.py");
  assert.match(routes, /@router\.post\("\/\{course_id\}\/enroll"/);
  assert.match(routes, /Depends\(require_roles\("student"\)\)/);
  assert.match(routes, /course\.publication_status != "PUBLISHED"/);
});

test("student dashboard opens the enrolled learning workspace", async () => {
  const dashboard = await read("../components/auth/RoleDashboard.js");
  assert.match(dashboard, /\/courses\/\$\{course\.id\}\/workspace/);
  assert.match(dashboard, /Explore published courses/);
});

test("course enrollment opens the course learning workspace", async () => {
  const catalog = await read("../pages/courses/index.js");
  const detail = await read("../pages/courses/[id].js");
  assert.match(
    catalog,
    /router\.push\(`\/courses\/\$\{course\.id\}\/workspace`\)/,
  );
  assert.match(
    detail,
    /router\.push\(`\/courses\/\$\{course\.id\}\/workspace`\)/,
  );
});

test("workspace renders complete syllabus and meaningful empty states", async () => {
  const workspace = await read("../pages/courses/[id]/workspace.js");
  assert.match(workspace, /Subject → Unit → Topic → Subtopic/);
  assert.match(workspace, /Remedial learning/);
  assert.match(workspace, /Mastery practice/);
  assert.match(workspace, /No subject expert has been assigned yet/);
  assert.doesNotMatch(workspace, /My subject review requests/);
  assert.doesNotMatch(workspace, /SUBJECT EXPERT RESPONSIBILITY/);
  assert.match(workspace, /downloadCourseProfilePdf/);
  assert.match(workspace, /Download course information PDF/);
});
