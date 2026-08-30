import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const read = (p) => fs.readFileSync(new URL(p, import.meta.url), "utf8");
const { syllabusPagePath, subjectBranch } = await import(`data:text/javascript;base64,${Buffer.from(read("../src/syllabusPages.js")).toString("base64")}`);
test("separate page URLs preserve selected review and role", () => {
  assert.equal(syllabusPagePath("admin", 2), "/admin/courses/2/syllabus");
  assert.equal(syllabusPagePath("super_admin", 2, "upload", 12), "/admin/courses/2/syllabus/upload?review=12");
  assert.equal(syllabusPagePath("faculty", 2, "reviews", 12), "/courses/2/syllabus/reviews?review=12");
  assert.equal(syllabusPagePath("faculty", 2, "approved", 12), "/courses/2/syllabus/approved");
});
test("subject filtering preserves descendants and excludes another subject", () => {
  const nodes = [{key:"s1",level:"subject"},{key:"s2",level:"subject"},{key:"u",level:"unit",parent:"s1"},{key:"t",level:"topic",parent:"u"},{key:"st",level:"subtopic",parent:"t"}];
  assert.deepEqual(subjectBranch(nodes,"s1").map(n=>n.key),["s1","u","t","st"]);
  assert.deepEqual(subjectBranch(nodes,"s2").map(n=>n.key),["s2"]);
  assert.deepEqual(subjectBranch(nodes,"missing"),[]);
});
test("every page has a route; admin routes retain a single admin shell", () => {
  for (const page of ["upload","reviews","approved"]) {
    const admin = read(`../pages/admin/courses/[id]/syllabus/${page}.js`);
    assert.ok(admin.includes(`page="${page}"`));
    assert.match(admin,/getLayout = \(page\) => page/);
    assert.ok(read(`../pages/courses/[id]/syllabus/${page}.js`).includes(`page="${page}"`));
  }
  assert.match(read("../pages/courses/[id]/syllabus/index.js"),/page="structure"/);
  assert.match(read("../pages/courses/[id]/syllabus-review.js"),/page="reviews"/);
});
test("editing, Excel, and review decisions have separate page gates", () => {
  const ui = read("../components/syllabus/SyllabusReviewWorkspace.js");
  assert.match(ui,/page === "upload" && canEdit && data.can_manage/);
  assert.match(ui,/page === "reviews" && review.status === "SUBMITTED"/);
  assert.match(ui,/editable=\{page === "structure" && canEdit/);
  assert.match(ui,/page === "approved" && <section/);
  assert.match(ui,/dirty \|\| editing \|\| preview/);
  assert.match(ui,/href=\{pageHref\(key\)\}/);
  assert.doesNotMatch(ui,/href="#syllabus-/);
});
