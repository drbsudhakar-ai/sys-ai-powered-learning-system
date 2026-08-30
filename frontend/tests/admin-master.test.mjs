import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/adminMaster.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const adminMaster = await import(moduleUrl);

test("student master query persists supported URL state", () => {
  const query = adminMaster.masterQueryFromRouter({
    search: "ROLL-21",
    status: "active",
    college: "SYS College",
    programme_id: "4",
    admission_year: "2026",
    present_year: "1",
    page: "3",
    page_size: "50",
    sort: "roll_number",
    order: "desc",
  }, "student");
  assert.equal(query.search, "ROLL-21");
  assert.equal(query.status, "active");
  assert.equal(query.page, 3);
  assert.equal(query.page_size, 50);
  assert.equal(query.sort, "roll_number");
  assert.equal(query.order, "desc");
  assert.equal(query.programme_id, "4");
});

test("invalid URL paging and status values fall back safely", () => {
  const query = adminMaster.masterQueryFromRouter({ page: "-4", page_size: "500", status: "invented" }, "faculty");
  assert.equal(query.page, 1);
  assert.equal(query.page_size, 25);
  assert.equal(query.status, "all");
});

test("student programme label prioritizes the institutional academic programme", () => {
  assert.equal(
    adminMaster.studentProgrammeLabel({ academic_program: "B.Sc.(MPCS)", programmes: [{ id: 1, title: "GATE Preparation" }] }),
    "B.Sc.(MPCS)",
  );
  assert.equal(adminMaster.studentProgrammeLabel({ academic_program: "  B.Com  " }), "B.Com");
});

test("student programme label falls back to SYS enrolments when needed", () => {
  assert.equal(
    adminMaster.studentProgrammeLabel({ academic_program: null, programmes: [{ id: 1, title: "NEET" }, { id: 2, title: "English Communication" }] }),
    "NEET, English Communication",
  );
  assert.equal(adminMaster.studentProgrammeLabel({ academic_program: "", programmes: [] }), "Unavailable");
  assert.equal(adminMaster.studentProgrammeLabel(null), "Unavailable");
});

test("edit forms normalize legacy academic and employment status values", () => {
  assert.equal(adminMaster.normalizeMasterStatus("Active"), "ACTIVE");
  assert.equal(adminMaster.normalizeMasterStatus(" inactive "), "INACTIVE");
  assert.equal(adminMaster.normalizeMasterStatus("unknown"), "ACTIVE");
});

test("profile photo validation accepts supported images within five MB", () => {
  assert.equal(adminMaster.validateProfilePhoto({ type: "image/jpeg", size: 1024 }), "");
  assert.match(adminMaster.validateProfilePhoto({ type: "image/gif", size: 1024 }), /JPEG, PNG or WebP/);
  assert.match(adminMaster.validateProfilePhoto({ type: "image/png", size: 6 * 1024 * 1024 }), /5 MB/);
});

test("student and faculty edit routes use the shared SYS administrator workspace", async () => {
  const student = await readFile(new URL("../pages/admin/students/[id]/edit.js", import.meta.url), "utf8");
  const faculty = await readFile(new URL("../pages/admin/faculty/[id]/edit.js", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../components/admin/MasterRecordEditPage.js", import.meta.url), "utf8");
  assert.match(student, /MasterRecordEditPage kind="student"/);
  assert.match(faculty, /MasterRecordEditPage kind="faculty"/);
  assert.match(workspace, /<AdminShell/);
  assert.match(workspace, /type="file"/);
  assert.doesNotMatch(workspace, /Profile Photo URL/);
  assert.match(workspace, /record\.registration_complete === true/);
  assert.match(workspace, /form\.photo_url/);
  assert.match(workspace, /Pending registration/);
});

test("master response validation rejects malformed success payloads", () => {
  const valid = {
    items: [{ id: 1, name: "Student", registration_status: "ACTIVE", is_active: true, mobile_number: "+919876540021", mobile_masked: "••••••0021" }],
    total: 1,
    page: 1,
    page_size: 25,
  };
  assert.equal(adminMaster.isMasterPageResponse(valid), true);
  assert.equal(adminMaster.isMasterPageResponse({ ...valid, items: [] }), true);
  assert.equal(adminMaster.isMasterPageResponse({ ...valid, total: "1" }), false);
  assert.equal(adminMaster.isMasterPageResponse({ ...valid, items: [{ id: 1, name: "Student" }] }), false);
  assert.equal(adminMaster.isMasterPageResponse({ ...valid, items: [{ ...valid.items[0], mobile_number: 9876540021 }] }), false);
});

test("operations summary requires every consumed dashboard field", () => {
  const summary = {
    generated_at: new Date().toISOString(),
    unread_notifications: 0,
    students: { total: 0, active: 0, pending_activation: 0 },
    faculty: { total: 0, active: 0, pending_activation: 0 },
    programmes: { total: 0, active: 0, draft: 0 },
    attention_required: { total: 0 },
    attention: [{ key: "pending", label: "Pending", count: 0, href: "/admin/students" }],
    readiness: [{ key: "masters", label: "Masters", status: "needs_attention", detail: "No records." }],
    academic_operations: { programmes: 0, subjects: 0, coordinator_assignments: 0, expert_assignments: 0 },
    recent_operations: { assessments: [], learning_sessions: [] },
    early_warning: { students_requiring_attention: 0 },
    recent_admin_activity: { available: false, items: [], reason: "Restricted" },
  };
  assert.equal(adminMaster.isOperationsSummary(summary), true);
  assert.equal(adminMaster.isOperationsSummary({ ...summary, recent_operations: {} }), false);
  assert.equal(adminMaster.isOperationsSummary({ ...summary, students: { total: "0" } }), false);
});

test("compact query removes empty filters without removing valid paging", () => {
  assert.deepEqual(
    adminMaster.compactQuery({ search: "", college: null, page: 1, page_size: 25, status: "all" }),
    { page: 1, page_size: 25, status: "all" },
  );
});
