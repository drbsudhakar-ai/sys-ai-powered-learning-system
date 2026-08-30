import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const nav = await import(
  `data:text/javascript;base64,${Buffer.from(read("../src/workspaceNavigation.js")).toString("base64")}`
);

test("administrators return to Course Master and role-specific syllabus routes", () => {
  for (const role of ["admin", "super_admin"]) {
    assert.deepEqual(nav.courseListLink(role), {
      href: "/admin/courses",
      label: "Back to Course Master",
    });
    assert.equal(nav.courseHomeLink(role, 2).href, "/admin/courses/2");
    assert.equal(nav.syllabusLink(role, 2), "/admin/courses/2/syllabus");
  }
});
test("faculty and students retain their shared role workspaces", () => {
  assert.deepEqual(nav.courseListLink("faculty"), {
    href: "/faculty/coordinator-courses",
    label: "Back to Coordinator Courses",
  });
  assert.equal(nav.courseListLink("student").label, "Back to My Courses");
  assert.equal(nav.courseHomeLink("faculty", 2).href, "/courses/2/workspace");
  assert.equal(nav.syllabusLink("faculty", 2), "/courses/2/syllabus");
  assert.equal(nav.administratorRole("student"), false);
  assert.equal(nav.administratorRole(undefined), false);
});

test("faculty coordinator returns to the scoped coordinator-course page", () => {
  assert.equal(
    nav.courseListLink("faculty").href,
    "/faculty/coordinator-courses",
  );
});
test("shared admin shell returns before the public header; public routes remain public", () => {
  const layout = read("../components/Layout.js");
  assert.match(
    layout,
    /session\.status === "authenticated"\s*&&\s*session\.user\?\.is_active\s*&&\s*administratorRole\(role\)\s*&&\s*!publicRoutes\.includes\(router\.pathname\)/,
  );
  assert.ok(layout.indexOf("<AdminShell") < layout.indexOf("<SYSHeader"));
  assert.match(layout, /<RoleWorkspaceShell role=\{role\}/);
});
test("syllabus management exposes upload and full hierarchy without bypassing approval", () => {
  const ui = read("../components/syllabus/SyllabusReviewWorkspace.js");
  assert.match(ui, /Syllabus management pages/);
  assert.match(ui, /Start editing/);
  assert.match(
    ui,
    /page === "upload" && canEdit && data.can_manage && <section id="syllabus-excel"/,
  );
  assert.match(ui, /data.revision > 0 && <ApprovedSyllabusDownload/);
  assert.match(ui, /editableReview\(r, data.actor_id\)/);
  assert.match(
    ui,
    /mayStructure \|\| \["topic", "subtopic"\].includes\(level\)/,
  );
  assert.match(ui, /<select required value=\{editing.parent/);
  assert.match(ui, /Save & submit for approval/);
  assert.match(ui, /Approve complete proposal/);
});
