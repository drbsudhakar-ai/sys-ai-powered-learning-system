import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { courseStatusLabel } from "../src/courseMaster.js";

test("publication lifecycle has professional explicit status labels", () => {
  assert.equal(courseStatusLabel({ publication_status: "READY_FOR_REVIEW" }), "Ready for review");
  assert.equal(courseStatusLabel({ publication_status: "PUBLISHED" }), "Published");
  assert.equal(courseStatusLabel({ publication_status: "ARCHIVED" }), "Archived");
});

test("course profile provides readiness-gated lifecycle controls", async () => {
  const source = await readFile(new URL("../components/admin/CourseProfilePage.js", import.meta.url), "utf8");
  for (const label of ["Course publication readiness", "Submit for review", "Publish course", "Return to draft", "Archive course"]) {
    assert.ok(source.includes(label), label);
  }
});

test("frontend uses dedicated controlled publication API routes", async () => {
  const source = await readFile(new URL("../src/api.js", import.meta.url), "utf8");
  for (const path of ["publication-readiness", "submit-for-review", "/publish", "return-to-draft", "/archive"]) {
    assert.ok(source.includes(path), path);
  }
});
