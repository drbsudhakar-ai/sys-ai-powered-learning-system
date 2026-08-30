import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("../src/courseReports.js", import.meta.url),
  "utf8",
);
const reports = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);

test("course reports preserve the authorized backend-generated PDF filename", () => {
  const response = {
    headers: {
      "content-disposition":
        'attachment; filename="SYS_Course_Profile_NEET-2027_2026-08-24.pdf"',
    },
  };
  assert.equal(
    reports.courseReportFilename(response),
    "SYS_Course_Profile_NEET-2027_2026-08-24.pdf",
  );
});

test("subject syllabus fallback filenames are safe and professionally labeled", () => {
  assert.equal(
    reports.courseReportFilename(
      {},
      { scope: "Subject", type: "Syllabus", identifier: "Physics / NEET" },
    ),
    "SYS_Subject_Syllabus_Weightages_Physics___NEET.pdf",
  );
});

test("multiple subject experts do not create duplicate subject report actions", () => {
  assert.deepEqual(
    reports
      .subjectReportRows([
        { subject_id: 10, faculty_name: "A" },
        { subject_id: 10, faculty_name: "B" },
        { subject_id: 11, faculty_name: "C" },
      ])
      .map((row) => row.subject_id),
    [10, 11],
  );
});

test("course profile offers complete course and assigned-subject PDF downloads", async () => {
  const profile = await readFile(
    new URL("../components/admin/CourseProfilePage.js", import.meta.url),
    "utf8",
  );
  for (const text of [
    "Download course profile PDF",
    "Download syllabus PDF",
    "Subject profile PDF",
    "Subject syllabus PDF",
    "downloadCourseProfilePdf",
    "downloadSubjectProfilePdf",
  ])
    assert.ok(profile.includes(text), text);
});

test("subject expert portfolio includes saved syllabus-review assignments", async () => {
  const routes = await readFile(
    new URL("../../backend/app/routes/admin.py", import.meta.url),
    "utf8",
  );
  const pdf = await readFile(
    new URL(
      "../../backend/app/services/course_profile_pdf.py",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(routes, /faculty_draft_assignments/);
  assert.match(routes, /_draft_subject_report_payload/);
  assert.match(routes, /subject-experts\/subject-information/);
  assert.match(pdf, /Assigned subjects across SYS courses/);
});

test("subject expert portfolio is concise and individual subject view owns detailed PDF", async () => {
  const api = await readFile(new URL("../src/api.js", import.meta.url), "utf8");
  const view = await readFile(
    new URL("../components/auth/SubjectExpertInformation.js", import.meta.url),
    "utf8",
  );
  const routes = await readFile(
    new URL("../../backend/app/routes/admin.py", import.meta.url),
    "utf8",
  );
  const pdf = await readFile(
    new URL(
      "../../backend/app/services/course_profile_pdf.py",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(pdf, /Assigned subjects across SYS courses/);
  assert.match(api, /downloadSubjectExpertInformationPdf/);
  assert.match(view, /Download subject information PDF/);
  assert.match(routes, /subject-information\.pdf/);
});

test("faculty report workspace limits subject visibility to assigned ownership", async () => {
  const page = await readFile(
    new URL("../pages/courses/[id]/reports.js", import.meta.url),
    "utf8",
  );
  assert.match(page, /ownership\?\.can_manage_course \|\| subject\.editable/);
  assert.match(page, /Reports limited to your assigned academic subjects/);
  assert.match(page, /Download subject syllabus PDF/);
});

test("course and subject PDF endpoints always request authenticated binary responses", async () => {
  const api = await readFile(new URL("../src/api.js", import.meta.url), "utf8");
  for (const action of [
    "downloadCourseProfilePdf",
    "downloadCourseSyllabusPdf",
    "downloadSubjectProfilePdf",
    "downloadSubjectSyllabusPdf",
    "downloadMyCoordinatorCoursesPdf",
    "downloadMySubjectExpertAssignmentsPdf",
  ])
    assert.match(
      api,
      new RegExp(`${action}[\\s\\S]{0,180}?responseType: "blob"`),
    );
});

test("course syllabus and ownership workspaces expose report entry points", async () => {
  const syllabus = await readFile(
    new URL("../components/admin/CourseSyllabusWorkspace.js", import.meta.url),
    "utf8",
  );
  const ownership = await readFile(
    new URL(
      "../components/admin/AcademicResponsibilitiesWorkspace.js",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(syllabus, /SyllabusReviewWorkspace/);
  assert.match(ownership, /Faculty course reports/);
});
