import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../src/auth.js", import.meta.url), "utf8");
const authModule = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);
const {
  REGISTRATION_ROLES,
  isAdminRole,
  isStaffRole,
  roleDisplayLabel,
  roleLandingPath,
} = authModule;


test("Super Admin receives administrator authorization and redirect", () => {
  assert.equal(isAdminRole("super_admin"), true);
  assert.equal(isStaffRole("super_admin"), true);
  assert.equal(roleLandingPath("super_admin"), "/admin-dashboard");
});

test("ordinary Admin keeps administrator authorization and redirect", () => {
  assert.equal(isAdminRole("admin"), true);
  assert.equal(roleLandingPath("admin"), "/admin-dashboard");
});

test("dashboard profile labels come from the authenticated role", () => {
  assert.equal(roleDisplayLabel("super_admin"), "Super Admin");
  assert.equal(roleDisplayLabel("admin"), "Administrator");
  assert.notEqual(roleDisplayLabel("super_admin"), roleDisplayLabel("admin"));
});

test("registration exposes only student and faculty roles", () => {
  assert.deepEqual(
    REGISTRATION_ROLES.map(({ value }) => value),
    ["student", "faculty"],
  );
  assert.equal(REGISTRATION_ROLES.some(({ value }) => isAdminRole(value)), false);
});
