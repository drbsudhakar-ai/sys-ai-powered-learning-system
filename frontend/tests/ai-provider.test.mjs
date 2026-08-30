import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const source = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("admin provider page uses protected shared shell and navigation", () => {
  const page = source("pages/admin/ai-provider.js");
  assert.match(page, /getLayout/);
  const ui = source("components/admin/AIProviderWorkspace.js");
  assert.match(ui, /useAdminAccess/);
  assert.match(ui, /<AdminShell/);
  assert.match(source("components/admin/AdminShell.js"), /\/admin\/ai-provider/);
});

test("credential stays transient and tests require saved settings", () => {
  const ui = source("components/admin/AIProviderWorkspace.js");
  assert.match(ui, /type="password"/);
  assert.doesNotMatch(ui, /localStorage|sessionStorage/);
  assert.match(ui, /disabled=\{busy \|\| dirty \|\| !config.revision\}/);
  assert.match(ui, /expected_revision/);
});

test("usage distinguishes measured tokens from local budgets", () => {
  const ui = source("components/admin/AIProviderWorkspace.js");
  for (const key of ["measured_tokens", "estimated_requests", "failed_requests", "budget_tokens", "student_daily_requests"]) assert.ok(ui.includes(key));
  assert.match(ui, /not a guarantee of free usage/);
});
