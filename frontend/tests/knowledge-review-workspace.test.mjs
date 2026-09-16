import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
const read = (path) => fs.readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("knowledge review workspace preserves preparation, expert verification and approval roles", () => {
  const ui = read("components/knowledge/KnowledgeReviewWorkspace.js");
  for (const phrase of ["Inspect complete package","Assign reviewer","Submit for expert review","Expert verify","Request corrections","Approve package"]) assert.match(ui, new RegExp(phrase));
  for (const phrase of ["Controlled pilot approval","Preview eligible packages","Approve all eligible for pilot","PILOT_APPROVED"]) assert.match(ui, new RegExp(phrase));
  assert.match(ui, /item\.status === "SOURCE_REVIEW"/); assert.match(ui, /item\.status === "EXPERT_VERIFIED"/);
});

test("administrator and faculty review pages opt out of the default shell", () => {
  const admin = read("pages/admin/courses/[id]/knowledge-reviews.js");
  const faculty = read("pages/faculty/academic-reviews.js");
  assert.match(admin, /AdminShell/); assert.match(admin, /getLayout/);
  assert.match(faculty, /RoleWorkspaceShell/); assert.match(faculty, /getLayout/);
});
