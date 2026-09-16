import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("Knowledge Studio exposes policy, guides, coverage, and honest future capabilities", () => {
  const ui = read("components/knowledge/CourseKnowledgeStudio.js");
  for (const text of ["Course Delivery Policy", "Subject Delivery Guides", "Topic and subtopic packages", "P036.2B", "P036.2C", "disabled"]) assert.match(ui, new RegExp(text));
  for (const field of ["audience", "teaching_objective", "required_lesson_stages", "delivery_requirements", "accuracy_requirements"]) assert.match(ui, new RegExp(field));
});

test("administrator and coordinator use the same governed workspace with distinct activation authority", () => {
  const admin = read("pages/admin/courses/[id]/knowledge-studio.js");
  const coordinator = read("pages/faculty/coordinator-courses/[courseId]/knowledge-studio.js");
  assert.match(admin, /canActivate/); assert.match(admin, /AdminShell/);
  assert.match(coordinator, /canActivate=\{false\}/); assert.match(coordinator, /RoleWorkspaceShell/);
  assert.match(admin, /getLayout = \(page\) => page/);
  assert.match(coordinator, /getLayout = \(page\) => page/);
});

test("course profile and coordinator responsibility cards link to Knowledge Studio", () => {
  assert.match(read("components/admin/CourseProfilePage.js"), /knowledge-studio/);
  assert.match(read("components/auth/FacultyResponsibilityCourses.js"), /knowledge-studio/);
  const api = read("src/api.js");
  for (const method of ["getCourseKnowledgeStudio", "createCourseTeachingPackRevision", "decideCourseTeachingPack", "saveSubjectDeliveryGuide"]) assert.match(api, new RegExp(method));
});
