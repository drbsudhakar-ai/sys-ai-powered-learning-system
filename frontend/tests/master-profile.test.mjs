import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/masterProfile.js", import.meta.url), "utf8");
const profile = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

test("profile initials support academic titles and dotted names", () => {
  assert.equal(profile.profileInitials("Dr. B Sudhakar"), "BS");
  assert.equal(profile.profileInitials("B.Yashaswi"), "BY");
  assert.equal(profile.profileInitials("AVUTI VIKAS"), "AV");
});

test("profile photos accept managed paths and web URLs but reject unsafe schemes", () => {
  assert.equal(profile.safeProfilePhotoUrl("/photos/student.jpg"), "/photos/student.jpg");
  assert.equal(profile.safeProfilePhotoUrl("https://example.com/faculty.png"), "https://example.com/faculty.png");
  assert.equal(profile.safeProfilePhotoUrl("javascript:alert(1)"), null);
  assert.equal(profile.safeProfilePhotoUrl("//example.com/photo.jpg"), null);
  assert.equal(profile.safeProfilePhotoUrl(""), null);
});

test("student and faculty photos are discovered automatically by institutional identifier", () => {
  assert.equal(profile.profilePhotoUrl({ employee_code: "602867" }, "faculty"), "/photos/faculty-602867.jpg");
  assert.equal(profile.profilePhotoUrl({ roll_number: "240334524681001" }, "student"), "/photos/student-240334524681001.jpg");
  assert.equal(profile.profilePhotoUrl({ employee_code: "602867", photo_url: "/photos/custom.png" }, "faculty"), "/photos/custom.png");
  assert.equal(profile.profilePhotoUrl({ employee_code: "../../private" }, "faculty"), null);
  assert.equal(profile.profilePhotoUrl({ employee_code: "602867", photo_url: "javascript:alert(1)" }, "faculty"), null);
});

test("master view opens the full profile directly without rendering an overlay", async () => {
  const workspace = await readFile(new URL("../components/admin/MasterWorkspace.js", import.meta.url), "utf8");
  assert.doesNotMatch(workspace, /setPreview\(record\)/);
  assert.doesNotMatch(workspace, /<RecordDrawer\s/);
  assert.match(workspace, /<Link href=\{`\/admin\/\$\{kind === "student" \? "students" : "faculty"\}\/\$\{record\.id\}`\}><EyeIcon/);
});

test("registration and activity labels remain administrator-friendly", () => {
  assert.equal(profile.profileStatusLabel("PENDING_ACTIVATION"), "Pending registration");
  assert.equal(profile.profileStatusLabel("ACTIVE"), "Active");
  assert.equal(profile.profileDateLabel(null), "Not available");
  assert.match(profile.profileDateLabel("2026-08-23T11:39:33Z"), /IST$/);
});

test("PDF download keeps the backend-provided safe filename", () => {
  assert.equal(
    profile.profileDownloadFilename({ headers: { "content-disposition": 'attachment; filename="SYS_Student_Profile_240334524681001_2026-08-23.pdf"' } }, "student", "240334524681001"),
    "SYS_Student_Profile_240334524681001_2026-08-23.pdf",
  );
});

test("student and faculty profiles preserve genuine enrollments and responsibility management", async () => {
  const component = await readFile(new URL("../components/admin/MasterRecordProfilePage.js", import.meta.url), "utf8");
  assert.match(component, /Registered SYS courses/);
  assert.match(component, /adminAssignCourseCoordinator/);
  assert.match(component, /adminAssignSubjectExpert/);
  assert.match(component, /adminRemoveCourseCoordinator/);
  assert.match(component, /adminRemoveSubjectExpert/);
  assert.match(component, /Download profile PDF/);
});

test("student profiles expose every SYS learning module with meaningful empty states", async () => {
  const component = await readFile(new URL("../components/admin/MasterRecordProfilePage.js", import.meta.url), "utf8");
  for (const title of [
    "Learning sessions and progress", "Assessment performance", "Performance analysis and learning gaps",
    "Remedial learning and interventions", "Topic mastery and adaptive practice", "Learning journey and next action",
    "Early warnings and student support", "English communication and skill development", "Notifications and engagement",
  ]) assert.ok(component.includes(title), `Missing student profile section: ${title}`);
  assert.match(component, /Learning has not started yet/);
  assert.match(component, /No assessments attempted yet/);
  assert.match(component, /Not registered for an English communication programme yet/);
});

test("faculty profiles expose teaching, assessments, oversight, remediation, content, and communication", async () => {
  const component = await readFile(new URL("../components/admin/MasterRecordProfilePage.js", import.meta.url), "utf8");
  for (const title of [
    "Teaching and learning sessions", "Assessment creation and evaluation", "Student performance and academic oversight",
    "Remedial guidance and interventions", "Question bank and academic content", "Communication and notifications",
  ]) assert.ok(component.includes(title), `Missing faculty profile section: ${title}`);
  assert.match(component, /No teaching or facilitated learning sessions have started yet/);
  assert.match(component, /No remedial groups or student interventions have been created yet/);
});
