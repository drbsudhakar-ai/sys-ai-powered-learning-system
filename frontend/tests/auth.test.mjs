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

test("student and faculty receive separate role dashboards", () => {
  assert.equal(roleLandingPath("student"), "/student-dashboard");
  assert.equal(roleLandingPath("faculty"), "/faculty-dashboard");
});

test("activation and recovery backend routes are complete", async () => {
  const routes = await readFile(new URL("../../backend/app/routes/auth.py", import.meta.url), "utf8");
  for (const route of [
    "/activation/start",
    "/activation/verify-otp",
    "/activation/verify-contact",
    "/activation/complete",
    "/password-reset/start",
    "/password-reset/verify-otp",
    "/password-reset/complete",
    "/dashboard",
  ]) {
    assert.ok(routes.includes(route), route);
  }
});

test("role dashboards enforce authenticated backend scope", async () => {
  const component = await readFile(new URL("../components/auth/RoleDashboard.js", import.meta.url), "utf8");
  assert.match(component, /getRoleDashboard/);
  assert.match(component, /payload\?\.role !== expectedRole/);
});

test("legacy dashboard securely redirects from authenticated role", async () => {
  const dashboard = await readFile(new URL("../pages/dashboard.js", import.meta.url), "utf8");
  assert.match(dashboard, /getMe\(\)/);
  assert.match(dashboard, /roleLandingPath\(data\?\.role\)/);
  assert.doesNotMatch(dashboard, /getCourses/);
});

test("pilot registration and recovery use available email OTP delivery", async () => {
  const registration = await readFile(new URL("../pages/register.js", import.meta.url), "utf8");
  const recovery = await readFile(new URL("../pages/forgot-password.js", import.meta.url), "utf8");
  assert.match(registration, /const ownershipChannel = "email"/);
  assert.doesNotMatch(registration, /phase === "mobileOtp"/);
  assert.match(recovery, /const channel = "email"/);
  assert.doesNotMatch(recovery, /setChannel/);
});

test("registration exposes only student and faculty roles", () => {
  assert.deepEqual(
    REGISTRATION_ROLES.map(({ value }) => value),
    ["student", "faculty"],
  );
  assert.equal(REGISTRATION_ROLES.some(({ value }) => isAdminRole(value)), false);
});

test("registration confirms minimal identity and masks institutional email", async () => {
  const registration = await readFile(new URL("../pages/register.js", import.meta.url), "utf8");
  const service = await readFile(new URL("../../backend/app/services/authentication.py", import.meta.url), "utf8");
  assert.match(registration, /Institutional record confirmed/);
  assert.match(registration, /Verification code sent to:/);
  assert.match(registration, /complete email address is not displayed/);
  assert.match(service, /mask_institutional_email/);
});

test("registration explains that personal email becomes the primary login email", async () => {
  const registration = await readFile(new URL("../pages/register.js", import.meta.url), "utf8");
  assert.match(registration, /personal email will become your primary SYS login email/);
  assert.match(registration, /Verify your personal login email/);
  assert.match(registration, /Use your verified personal email as your primary SYS login email/);
});
