import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("role dashboard delegates shared header and footer to the application shell", async () => {
  const component = await readFile(
    new URL("../components/auth/RoleDashboard.js", import.meta.url),
    "utf8",
  );

  assert.match(component, /getRoleDashboard/);
  assert.match(component, /payload\?\.role !== expectedRole/);
  assert.doesNotMatch(component, /import Layout from/);
  assert.doesNotMatch(component, /<Layout>/);
});

test("authenticated header loads managed profile photos from the frontend origin", async () => {
  const header = await readFile(
    new URL("../components/layout/SYSHeader.js", import.meta.url),
    "utf8",
  );

  assert.match(header, /user\?\.photo_url/);
  assert.match(header, /value\.startsWith\("\/"\) \? value : `\/\$\{value\}`/);
  assert.match(
    header,
    /Managed profile photographs are stored in Next\.js public\/photos/,
  );
});

test("faculty assigned-courses navigation exposes responsibility-aware child pages", async () => {
  const shell = await readFile(
    new URL("../components/auth/RoleWorkspaceShell.js", import.meta.url),
    "utf8",
  );
  const responsibility = await readFile(
    new URL(
      "../components/auth/FacultyResponsibilityCourses.js",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(shell, /Assigned Courses/);
  assert.match(shell, /\/faculty\/coordinator-courses/);
  assert.match(shell, /\/faculty\/subject-expert-courses/);
  assert.match(shell, /data\?\.courses\?\.length/);
  assert.match(shell, /data\?\.subjects\?\.length/);
  assert.match(responsibility, /Reviews & approvals/);
  assert.doesNotMatch(responsibility, /Reports & downloads/);
  assert.match(responsibility, /Download assigned courses PDF/);
  assert.match(responsibility, /downloadMyCoordinatorCoursesPdf/);
  assert.match(responsibility, /Download assigned subjects PDF/);
  assert.match(responsibility, /downloadMySubjectExpertAssignmentsPdf/);
  assert.match(responsibility, /Review recommended for final approval/);
  assert.match(responsibility, /View subject/);
  assert.match(
    responsibility,
    /subject-expert-courses\/\$\{course\.id\}\/subject/,
  );
});

test("subject experts have an ownership-scoped subject information workspace", async () => {
  const page = await readFile(
    new URL(
      "../pages/faculty/subject-expert-courses/[courseId]/subject.js",
      import.meta.url,
    ),
    "utf8",
  );
  const workspace = await readFile(
    new URL("../components/auth/SubjectExpertInformation.js", import.meta.url),
    "utf8",
  );
  const api = await readFile(new URL("../src/api.js", import.meta.url), "utf8");
  assert.match(page, /SubjectExpertInformation/);
  assert.match(workspace, /Subject syllabus/);
  assert.match(workspace, /Students enrolled in the course/);
  assert.match(workspace, /enrollment_scope/);
  assert.match(api, /getSubjectExpertInformation/);
});

test("authenticated role workspaces do not repeat the public header and footer", async () => {
  const layout = await readFile(
    new URL("../components/Layout.js", import.meta.url),
    "utf8",
  );
  const shell = await readFile(
    new URL("../components/auth/RoleWorkspaceShell.js", import.meta.url),
    "utf8",
  );
  const shellStyles = await readFile(
    new URL(
      "../components/auth/RoleWorkspaceShell.module.css",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(layout, /if \(roleWorkspace\)/);
  assert.match(layout, /return \(\s*<RoleWorkspaceShell/);
  assert.match(shellStyles, /\.sidebar\{position:sticky;top:0;height:100vh/);
  assert.match(shell, /getInboxUnreadCount/);
  assert.match(shell, /notificationButton/);
  assert.match(shell, /profileButton/);
});

test("shared workspaces expose linked breadcrumbs", async () => {
  const breadcrumbs = await readFile(
    new URL("../components/auth/WorkspaceBreadcrumbs.js", import.meta.url),
    "utf8",
  );
  const admin = await readFile(
    new URL("../components/admin/AdminShell.js", import.meta.url),
    "utf8",
  );
  assert.match(breadcrumbs, /aria-label="Breadcrumb"/);
  assert.match(breadcrumbs, /aria-current/);
  assert.match(admin, /BREADCRUMB_LINKS/);
});
