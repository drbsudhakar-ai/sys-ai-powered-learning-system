import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("student and faculty dashboards use the professional shared workspace", async () => {
  const dashboard = await read("../components/auth/RoleDashboard.js");
  const layout = await read("../components/Layout.js");
  const shell = await read("../components/auth/RoleWorkspaceShell.js");
  assert.match(dashboard, /View and edit profile/);
  assert.match(layout, /RoleWorkspaceShell/);
  assert.match(layout, /roleWorkspace/);
  assert.match(layout, /\["student", "faculty"\]/);
  for (const label of ["My profile", "My courses", "Learning sessions", "Assessments", "Notifications"]) {
    assert.ok(shell.includes(label), label);
  }
  assert.match(shell, /STUDENT_ITEMS/);
  assert.match(shell, /FACULTY_ITEMS/);
});

test("authenticated role workspace persists across learning routes", async () => {
  const layout = await read("../components/Layout.js");
  assert.match(layout, /!publicRoutes\.includes\(router\.pathname\)/);
  assert.match(layout, /<RoleWorkspaceShell role=\{role\} identity=\{session\.user\}>/);
  assert.doesNotMatch(layout, /<SYSFooter session=\{session\} \/>[\s\S]*<RoleWorkspaceShell/);
});

test("self-service profile keeps institutional data read-only", async () => {
  const page = await read("../pages/account/profile.js");
  const api = await read("../src/api.js");
  assert.match(page, /These master details can only be corrected by a SYS administrator/);
  assert.match(page, /Personal login email/);
  assert.match(page, /readOnly/);
  assert.match(page, /accept="image\/jpeg,image\/png,image\/webp"/);
  assert.match(api, /\/auth\/me\/profile/);
  assert.match(api, /\/auth\/me\/photo/);
});

test("workspace branding puts only the compact SYS symbol on a white tile", async () => {
  const header = await read("../components/layout/SYSHeader.js");
  const roleShell = await read("../components/auth/RoleWorkspaceShell.js");
  const adminShell = await read("../components/admin/AdminShell.js");

  for (const source of [header, roleShell, adminShell]) {
    assert.match(source, /SYS_Symbol_Compact_Transparent\.png/);
    assert.match(source, /SYS — Strengthen Your Skills/);
  }

  assert.doesNotMatch(roleShell, /SYS_Header_Logo_Dark\.png/);
  assert.doesNotMatch(adminShell, /SYS_Header_Logo_Dark\.png/);
});
