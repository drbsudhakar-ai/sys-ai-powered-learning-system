import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/academicOwnership.js", import.meta.url), "utf8");
const ownership = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const faculty = [{ id: 2, name: "Dr. Physics", employee_code: "FAC-02", department: "Physics", is_active: true }, { id: 3, name: "Dr. Inactive", department: "Chemistry", is_active: false }];
const courses = [{ id: 10, title: "NEET" }, { id: 11, title: "JEE" }];
const subjects = [{ id: 20, name: "Physics", course_id: 10 }, { id: 21, name: "Chemistry", course_id: 10 }];
const coordinators = [{ id: 30, faculty_id: 2, faculty_name: "Dr. Physics", course_id: 10, course_title: "NEET" }];
const experts = [{ id: 40, faculty_id: 2, faculty_name: "Dr. Physics", subject_id: 20, subject_name: "Physics", course_id: 10, course_title: "NEET" }];

test("academic responsibility rows preserve course-scoped coordinator and subject ownership", () => {
  const rows = ownership.responsibilityRows(coordinators, experts, faculty, subjects);
  assert.equal(rows.length, 2); assert.equal(rows[0].type, "course_coordinator"); assert.equal(rows[1].course_id, 10); assert.equal(rows[1].faculty.employee_code, "FAC-02");
});

test("ownership filters support faculty, employee code, course, role, and department", () => {
  const rows = ownership.responsibilityRows(coordinators, experts, faculty, subjects);
  assert.equal(ownership.filterResponsibilities(rows, { search: "FAC-02" }).length, 2);
  assert.equal(ownership.filterResponsibilities(rows, { type: "subject_expert", course: "10", department: "Physics" }).length, 1);
  assert.equal(ownership.filterResponsibilities(rows, { course: "11" }).length, 0);
});

test("ownership summary reports courses and subjects without assigned academic owners", () => {
  assert.deepEqual(ownership.ownershipSummary(courses, subjects, coordinators, experts), { coordinators: 1, experts: 1, coursesWithoutCoordinator: 1, subjectsWithoutExpert: 1 });
});

test("inactive faculty cannot be selected for academic responsibility", () => {
  assert.deepEqual(ownership.availableFaculty(faculty).map((person) => person.id), [2]);
});

test("academic responsibilities use the SYS administration shell without a duplicate global header", async () => {
  const shell = await readFile(new URL("../components/admin/AdminShell.js", import.meta.url), "utf8");
  const page = await readFile(new URL("../pages/admin/academic-responsibilities.js", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../components/admin/AcademicResponsibilitiesWorkspace.js", import.meta.url), "utf8");
  assert.match(shell, /href: "\/admin\/academic-responsibilities"/);
  assert.match(page, /\.getLayout = \(page\) => page;/);
  assert.match(workspace, /Subjects without expert/);
  assert.match(workspace, /courseSubjects/);
});

test("course profile links directly to course-scoped ownership management", async () => {
  const profile = await readFile(new URL("../components/admin/CourseProfilePage.js", import.meta.url), "utf8");
  assert.match(profile, /\/admin\/academic-responsibilities\?course_id=/);
  assert.match(profile, /No subject experts assigned yet/);
});
