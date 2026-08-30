import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/syllabus.js", import.meta.url), "utf8");
const syllabus = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

test("syllabus Excel template exposes the complete academic hierarchy", () => {
  assert.deepEqual(syllabus.SYLLABUS_COLUMNS.slice(0, 4), ["Subject", "Unit", "Topic", "Subtopic"]);
  assert.ok(syllabus.SYLLABUS_COLUMNS.includes("Unit Sequence"));
});

test("syllabus rows normalize optional values and preserve complete hierarchy", () => {
  const result = syllabus.normalizeSyllabusRows([{ Subject: " Physics ", Unit: " Mechanics ", Topic: " Motion ", Subtopic: " Velocity ", "Unit Sequence": "2" }]);
  assert.deepEqual(result.errors, []);
  assert.equal(result.rows[0].subject, "Physics");
  assert.equal(result.rows[0].unit, "Mechanics");
  assert.equal(result.rows[0].topic, "Motion");
  assert.equal(result.rows[0].subtopic, "Velocity");
  assert.equal(result.rows[0].unit_sequence, 2);
});

test("invalid syllabus rows include spreadsheet line numbers", () => {
  const result = syllabus.normalizeSyllabusRows([{ Subject: "Physics", Unit: "", Topic: "Motion", "Unit Sequence": 0.5 }]);
  assert.equal(result.errors.length, 2);
  assert.match(result.errors[0], /Row 2/);
  assert.match(result.errors[1], /positive whole number/);
});

test("syllabus counts derive from existing subjects, units, topics, and subtopics", () => {
  const tree = { subjects: [{ id: 1, units: [{ id: 2, topics: [{ id: 3, subtopics: [{ id: 4 }, { id: 5 }] }] }, { id: 6, topics: [] }] }] };
  assert.deepEqual(syllabus.syllabusCounts(tree), { subjects: 1, units: 2, topics: 1, subtopics: 2 });
  assert.deepEqual(syllabus.syllabusCounts(null), { subjects: 0, units: 0, topics: 0, subtopics: 0 });
});

test("the course profile and administrator route expose the branded syllabus workspace", async () => {
  const profile = await readFile(new URL("../components/admin/CourseProfilePage.js", import.meta.url), "utf8");
  const page = await readFile(new URL("../pages/admin/courses/[id]/syllabus.js", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../components/admin/CourseSyllabusWorkspace.js", import.meta.url), "utf8");
  assert.match(profile, /Manage syllabus/);
  assert.match(page, /\.getLayout = \(page\) => page/);
  assert.match(workspace, /SyllabusReviewWorkspace/);
  const review = await readFile(new URL("../components/syllabus/SyllabusReviewWorkspace.js", import.meta.url), "utf8");
  for (const phrase of ["Download blank template", "Upload workbook", "Save & submit for approval", "Approve complete proposal"]) assert.ok(review.includes(phrase), phrase);
});
