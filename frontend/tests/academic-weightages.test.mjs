import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/academicWeightages.js", import.meta.url), "utf8");
const weights = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

const tree = {
  course_id: 1, course_title: "NEET", can_manage_course: true,
  subjects: [{ id: 10, name: "Physics", weight_percent: 50, editable: true, units: [{ id: 20, name: "Mechanics", weight_percent: 100, topics: [{ id: 30, name: "Kinematics", weight_percent: 100, subtopics: [{ id: 40, name: "Motion", weight_percent: 60 }, { id: 41, name: "Velocity", weight_percent: 40 }] }] }] }, { id: 11, name: "Chemistry", weight_percent: 50, editable: true, units: [] }],
};

test("academic hierarchy exposes subject, unit, topic, and subtopic weightage groups", () => {
  const groups = weights.weightageGroups(tree);
  assert.deepEqual(groups.map((group) => group.level), ["subject", "unit", "topic", "subtopic", "unit"]);
  assert.equal(groups[0].parent_id, 1);
  assert.equal(groups[2].parent_id, 20);
});

test("weightage group totals must equal 100 percent without accepting incomplete values", () => {
  const group = weights.weightageGroups(tree)[0];
  assert.equal(weights.groupTotal(group.items), 100);
  assert.equal(weights.groupState(group.items), "complete");
  assert.equal(weights.groupState(group.items, { 10: "70", 11: "20" }), "invalid");
  assert.equal(weights.groupState([{ id: 1, weight_percent: null }]), "incomplete");
  assert.equal(weights.weightValue(-1), null);
  assert.equal(weights.weightValue(101), null);
});

test("equal distribution remains exactly 100 percent even across three siblings", () => {
  const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
  const values = weights.equalDistribution(items);
  assert.equal(weights.groupTotal(items, values), 100);
  assert.deepEqual(Object.values(values), ["33.34", "33.33", "33.33"]);
});

test("subject experts cannot edit course-level or unassigned subject groups", () => {
  const scoped = { ...tree, can_manage_course: false, subjects: tree.subjects.map((subject) => ({ ...subject, editable: subject.id === 10 })) };
  const groups = weights.weightageGroups(scoped);
  assert.equal(groups.some((group) => group.level === "subject"), false);
  assert.equal(groups.find((group) => group.level === "unit" && group.parent_id === 10).editable, true);
  assert.equal(groups.find((group) => group.level === "unit" && group.parent_id === 11).editable, false);
});

test("weightage readiness ignores empty groups and counts independently complete sibling groups", () => {
  assert.deepEqual(weights.weightageReadiness(tree), { groups: 4, completed: 4, pending: 0, percent: 100 });
  assert.deepEqual(weights.weightageReadiness(null), { groups: 0, completed: 0, pending: 0, percent: 0 });
});

test("pilot readiness reports completed course-weight coverage", () => {
  const pilot = {
    ...tree, pilot: true,
    subjects: [
      { ...tree.subjects[0], weight_percent: 12.5, governance: { complete: true } },
      { ...tree.subjects[1], weight_percent: 25, governance: { complete: true } },
      { id: "pending", name: "Pending", weight_percent: 62.5, units: [], governance: { complete: false } },
    ],
  };
  const readiness = weights.weightageReadiness(pilot);
  assert.equal(readiness.percent, 37.5);
  assert.equal(readiness.coveredPercent, 37.5);
});

test("save payload retains exact level, parent, and syllabus item identifiers", () => {
  const group = weights.weightageGroups(tree)[3];
  assert.deepEqual(weights.groupPayload(group, { 40: "55", 41: "45" }), { level: "subtopic", parent_id: 30, items: [{ item_id: 40, weight_percent: 55 }, { item_id: 41, weight_percent: 45 }] });
});

test("pilot save payload retains stable draft keys instead of live numeric ids", () => {
  const group = { level: "unit", parent_id: "new:english", items: [{ id: "new:grammar", weight_percent: 100 }] };
  assert.deepEqual(weights.pilotGroupPayload(group, {}, 2), {
    level: "unit", parent_key: "new:english",
    items: [{ item_key: "new:grammar", weight_percent: 100 }],
  });
});

test("course weightage route uses SYS administration shell without duplicate global header", async () => {
  const page = await readFile(new URL("../pages/admin/courses/[id]/weightages.js", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../components/admin/CourseWeightageWorkspace.js", import.meta.url), "utf8");
  assert.match(page, /\.getLayout = \(page\) => page;/);
  assert.match(workspace, /Every sibling group is saved independently/);
  assert.match(workspace, /Distribute equally/);
  assert.match(workspace, /Enable controlled pilot/);
  assert.match(workspace, /do not constitute institutional approval/);
  assert.match(workspace, /rows="4"/);
  assert.match(workspace, /Record the academic verification/);
});

test("weightage recommendation comment has a visible accessible textarea", async () => {
  const workspace = await readFile(new URL("../components/admin/CourseWeightageWorkspace.js", import.meta.url), "utf8");
  const globalStyles = await readFile(new URL("../styles/globals.css", import.meta.url), "utf8");
  assert.match(workspace, /function RoleWorkspaceContent/);
  assert.doesNotMatch(workspace, /\? \(\{ children \}\) => children/);
  assert.match(globalStyles, /min-height: 96px/);
  assert.match(globalStyles, /textarea\[placeholder\^="Record the academic verification"\]/);
});

test("course profile and syllabus both link to the academic weightage workspace", async () => {
  const profile = await readFile(new URL("../components/admin/CourseProfilePage.js", import.meta.url), "utf8");
  const syllabus = await readFile(new URL("../components/admin/CourseSyllabusWorkspace.js", import.meta.url), "utf8");
  assert.match(profile, /\/weightages`}>Manage academic weightages/);
  assert.match(syllabus, /\/weightages`} className/);
});
