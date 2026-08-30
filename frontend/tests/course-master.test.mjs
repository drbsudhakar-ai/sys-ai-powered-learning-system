import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/courseMaster.js", import.meta.url), "utf8");
const courses = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

test("course categories use the exact supported backend values", () => {
  assert.deepEqual(courses.COURSE_CATEGORIES.map(({ value }) => value), ["HIGHER_EDUCATION_ENTRANCE", "EMPLOYMENT_EXAM", "INDEPENDENT_LEARNING", "SKILL_DEVELOPMENT"]);
  assert.equal(courses.isExaminationCourse("HIGHER_EDUCATION_ENTRANCE"), true);
  assert.equal(courses.isExaminationCourse("INDEPENDENT_LEARNING"), false);
});

test("course creation requires a safe code and category-aware examination details", () => {
  const form = { title: "NEET Preparation", programme_code: "NEET-2027", programme_category: "HIGHER_EDUCATION_ENTRANCE", examination_name: "NEET" };
  assert.equal(courses.validateCourseForm(form), "");
  assert.match(courses.validateCourseForm({ ...form, programme_code: "" }), /code is required/i);
  assert.match(courses.validateCourseForm({ ...form, examination_name: "" }), /examination name/i);
  assert.match(courses.validateCourseForm({ ...form, programme_code: "bad code" }), /only letters/i);
  assert.match(courses.validateCourseForm({ ...form, syllabus_url: "javascript:alert(1)" }), /http/i);
});

test("English Communication retains its existing independent-learning backend rule", () => {
  const form = { title: "English Communication", programme_code: "ENGLISH_COMMUNICATION", programme_category: "INDEPENDENT_LEARNING" };
  assert.equal(courses.validateCourseForm(form), "");
  assert.match(courses.validateCourseForm({ ...form, programme_category: "SKILL_DEVELOPMENT" }), /independent learning/i);
});

test("course payload normalizes codes and removes irrelevant examination values", () => {
  const payload = courses.coursePayload({ title: "  English Communication  ", programme_code: " eng-course ", programme_category: "SKILL_DEVELOPMENT", examination_name: "NEET", examination_authority: "Example", is_active: false });
  assert.equal(payload.title, "English Communication");
  assert.equal(payload.programme_code, "ENG-COURSE");
  assert.equal(payload.examination_name, null);
  assert.equal(payload.examination_authority, null);
  assert.equal(payload.is_active, false);
});

test("course master filters search, category, active state, readiness, and sorting", () => {
  const items = [{ id: 1, title: "NEET", programme_code: "NEET-2027", programme_category: "HIGHER_EDUCATION_ENTRANCE", examination_name: "NEET", is_active: true, subject_count: 0, student_count: 4, course_coordinators: [] }, { id: 2, title: "English Communication", programme_code: "ENGLISH_COMMUNICATION", programme_category: "INDEPENDENT_LEARNING", is_active: false, subject_count: 1, student_count: 8, course_coordinators: [{ faculty_name: "Dr. Sudhakar" }] }];
  assert.equal(courses.filterCourses(items, { search: "sudhakar" })[0].id, 2);
  assert.equal(courses.filterCourses(items, { status: "active" })[0].id, 1);
  assert.equal(courses.filterCourses(items, { status: "draft" })[0].id, 2);
  assert.equal(courses.filterCourses(items, { status: "needs_attention" })[0].id, 1);
  assert.equal(courses.filterCourses(items, { sort: "students" })[0].id, 2);
});

test("course readiness does not invent syllabus, coordinator, or enrollment data", () => {
  const readiness = courses.courseReadiness({ title: "NEET", programme_code: "NEET-2027", subject_count: 0, student_count: 0, course_coordinators: [] });
  assert.equal(readiness[0].complete, true);
  assert.equal(readiness[1].complete, false);
  assert.equal(readiness[2].complete, false);
  assert.equal(readiness[3].complete, false);
});

test("course export protects Excel against executable formula values", () => {
  const csv = courses.courseCsv([{ title: "=CMD()", programme_code: "NEET", programme_category: "HIGHER_EDUCATION_ENTRANCE", is_active: true }]);
  assert.match(csv, /"'=CMD\(\)"/);
  assert.match(csv, /Course Code/);
});

test("administrator Course Master preserves shared student and faculty course routes", async () => {
  const shell = await readFile(new URL("../components/admin/AdminShell.js", import.meta.url), "utf8");
  const dashboard = await readFile(new URL("../pages/admin-dashboard.js", import.meta.url), "utf8");
  assert.match(shell, /label: "Course Master", href: "\/admin\/courses"/);
  assert.match(dashboard, /href: "\/admin\/courses\/new"/);
});

test("every administrator course page uses the existing SYS shell without a duplicate global header", async () => {
  for (const path of ["index.js", "new.js", "[id].js", "[id]/edit.js"]) {
    const page = await readFile(new URL(`../pages/admin/courses/${path}`, import.meta.url), "utf8");
    assert.match(page, /\.getLayout = \(page\) => page;/, path);
  }
});

test("the course profile preserves honest academic empty states and the agreed later phases", async () => {
  const profile = await readFile(new URL("../components/admin/CourseProfilePage.js", import.meta.url), "utf8");
  for (const phrase of ["No subjects configured yet", "No course coordinator assigned yet", "No students enrolled yet", "Learning has not started yet", "No assessments created yet", "Academic weightages have not been configured yet", "Course → Subject → Unit → Topic → Subtopic"]) {
    assert.ok(profile.includes(phrase), `Missing course readiness detail: ${phrase}`);
  }
  assert.equal(courses.COURSE_SETUP_PHASES.length, 5);
});
