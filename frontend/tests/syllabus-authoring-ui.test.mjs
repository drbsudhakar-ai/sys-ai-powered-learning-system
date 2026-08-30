import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const ui = fs.readFileSync(new URL("../components/syllabus/SyllabusReviewWorkspace.js", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../components/syllabus/SyllabusReview.module.css", import.meta.url), "utf8");
test("review metadata and baseline controls are restricted to the reviews page", () => {
  assert.match(ui, /page === "reviews" && <>\s*<h2>Review #/);
  assert.match(ui, /page === "reviews" && <label>Review summary \/ reason/);
  assert.match(ui, /page === "reviews" && review.decision_comment/);
  assert.match(ui, /page === "reviews" && <><div className=\{styles.actions\}><button onClick=\{\(\) => setShowBaseline/);
  assert.doesNotMatch(ui, /Working draft #|Saved drafts|Open review & submission/);
});
test("authoring uses a compact save toolbar and upload validation, not approval comparisons", () => {
  assert.match(ui, /authoring && <div className=\{styles.authoringHeading\}/);
  assert.match(ui, />Save syllabus<\/button>/);
  assert.match(ui, /Validation preview/);
  assert.match(ui, /preview.nodes.slice\(0, 30\)/);
  assert.doesNotMatch(ui, /<Comparison changes=\{preview.changes\}/);
  assert.match(ui, /page === "reviews" && canEdit && <div/);
});
test("authoring layout has responsive upload steps and a bounded subject navigator", () => {
  assert.match(css, /grid-template-columns: 240px minmax\(0,1fr\)/);
  assert.match(css, /\.uploadSteps \{ display: grid/);
  assert.match(css, /@media\(max-width:1100px\).*\.uploadSteps \{ grid-template-columns: 1fr/);
  assert.match(css, /\.previewTable \{ overflow-x: auto/);
});
