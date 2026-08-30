import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(new URL("../components/syllabus/SyllabusReviewWorkspace.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../components/syllabus/SyllabusReview.module.css", import.meta.url), "utf8");

test("workbook control explicitly supports browsing and drag and drop", () => {
  assert.match(component, /Drag and drop your workbook here/);
  assert.match(component, /Browse files/);
  assert.match(component, /onDragEnter=/);
  assert.match(component, /onDrop=/);
  assert.match(component, /validateWorkbook\(e\.dataTransfer\.files\?\.\[0\]\)/);
  assert.match(css, /\.dropZone/);
  assert.match(css, /\.uploadIcon/);
});

test("selected workbook and validation state remain visible", () => {
  assert.match(component, /uploadFile\.name/);
  assert.match(component, /Validation complete — preview ready/);
  assert.match(component, /Preview completed — content applied/);
  assert.match(component, /setUploadStatus\("applied"\)/);
});

test("save is gated by applied content and reports upload success", () => {
  assert.match(component, /page === "upload" && uploadStatus !== "applied"/);
  assert.match(component, /Click <b>Save syllabus<\/b> to complete the upload/);
  assert.match(component, /Syllabus uploaded successfully\. It is saved and ready for review and approval\./);
  assert.match(component, /if \(page === "upload"\)[\s\S]*setUploadStatus\("saved"\)[\s\S]*Syllabus uploaded successfully/);
});
