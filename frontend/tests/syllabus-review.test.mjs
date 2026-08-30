import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const source = fs.readFileSync(
  new URL("../src/syllabusReview.js", import.meta.url),
  "utf8",
);
const { ordered, reorder, editableReview, diffNodes, parseWorkbook } =
  await import(
    `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
  );
const nodes = [
  { key: "topic:1", parent: "unit:1", level: "topic", name: "A", sequence: 1 },
  { key: "topic:2", parent: "unit:1", level: "topic", name: "B", sequence: 2 },
  { key: "topic:3", parent: "unit:2", level: "topic", name: "C", sequence: 1 },
];
test("reordering preserves identity and other parents", () => {
  const moved = reorder(nodes, "topic:2", -1);
  assert.deepEqual(
    ordered(moved, "unit:1").map((n) => n.key),
    ["topic:2", "topic:1"],
  );
  assert.deepEqual(moved[2], nodes[2]);
  assert.equal(nodes[0].sequence, 1);
});
test("boundary moves are harmless", () =>
  assert.deepEqual(reorder(nodes, "topic:1", -1), nodes));
test("submitted proposals and other authors are read-only", () => {
  assert.equal(editableReview(null, undefined), false);
  assert.ok(editableReview({ author_id: 1, status: "DRAFT" }, 1));
  assert.ok(editableReview({ author_id: 1, status: "CHANGES_REQUESTED" }, 1));
  assert.ok(!editableReview({ author_id: 1, status: "SUBMITTED" }, 1));
  assert.ok(!editableReview({ author_id: 1, status: "DRAFT" }, 2));
});
test("renames are updates not new nodes", () => {
  const diff = diffNodes(
    nodes,
    nodes.map((n) => (n.key === "topic:1" ? { ...n, name: "Renamed" } : n)),
  );
  assert.equal(diff.length, 1);
  assert.equal(diff[0].kind, "Updated");
  assert.equal(diff[0].after.key, "topic:1");
});
test("old flat workbooks fail with actionable guidance", () =>
  assert.throws(() => parseWorkbook({ Sheets: {} }, {}), /old flat template/));
test("faculty upload controls require management permission", () => {
  const ui = fs.readFileSync(
    new URL(
      "../components/syllabus/SyllabusReviewWorkspace.js",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(ui, /canEdit && data.can_manage/);
  assert.match(ui, /Approve complete proposal/);
  assert.match(ui, /Before|Comparison/);
});
test("approved syllabus download appears in student and faculty course workspace", () => {
  const ui = fs.readFileSync(
    new URL("../pages/courses/[id]/workspace.js", import.meta.url),
    "utf8",
  );
  assert.match(ui, /ApprovedSyllabusDownload/);
  assert.match(ui, /subjectId={subject.id}/);
});
test("dual-role faculty can explicitly open subject-expert mode", () => {
  const dashboard = fs.readFileSync(
    new URL(
      "../components/syllabus/SubjectReviewDashboard.js",
      import.meta.url,
    ),
    "utf8",
  );
  const responsibility = fs.readFileSync(
    new URL(
      "../components/auth/FacultyResponsibilityCourses.js",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(responsibility, /mode=expert/);
  assert.match(dashboard, /router\.query\.mode === ["']expert["']/);
  assert.match(dashboard, /Subject Expert Review/);
  assert.match(dashboard, /data\.can_manage\s*&&\s*!expertMode/);
});
test("administrator final approval opens in an accessible recommendation modal", () => {
  const dashboard = fs.readFileSync(
    new URL(
      "../components/syllabus/SubjectReviewDashboard.js",
      import.meta.url,
    ),
    "utf8",
  );
  const styles = fs.readFileSync(
    new URL(
      "../components/syllabus/SyllabusReview.module.css",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(dashboard, /Open expert recommendation/);
  assert.match(dashboard, /role=.*dialog/);
  assert.match(dashboard, /aria-modal/);
  assert.match(dashboard, /data\?\.can_manage/);
  assert.match(dashboard, /data\.can_final_approve/);
  assert.match(dashboard, /Close expert recommendation/);
  assert.match(dashboard, /Finally approve subject/);
  assert.match(dashboard, /Return for changes/);
  assert.match(styles, /\.approvalBackdrop/);
  assert.match(styles, /position:fixed/);
});
