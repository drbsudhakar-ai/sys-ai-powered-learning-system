import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("landing header uses a readable symbol and live brand text", async () => {
  const landing = await read("../components/landing/LandingPage.js");

  assert.match(landing, /SYS_Symbol_Compact_Transparent\.png/);
  assert.match(landing, /<strong>SYS — Strengthen Your Skills<\/strong>/);
  assert.match(landing, /<small>AI-Powered Learning Platform<\/small>/);
});

test("shared authentication shell uses the current readable SYS brand", async () => {
  const authShell = await read("../components/auth/AuthShell.js");

  assert.match(authShell, /SYS_Symbol_Compact_Transparent\.png/);
  assert.match(authShell, /<strong>SYS — Strengthen Your Skills<\/strong>/);
  assert.match(authShell, /<small>AI-Powered Learning Platform<\/small>/);
  assert.doesNotMatch(authShell, /SYS_Header_Logo_Dark\.png/);
});

test("landing hero presents the new message and motion-safe 3D learning workspace", async () => {
  const [landing, styles] = await Promise.all([
    read("../components/landing/LandingPage.js"),
    read("../components/landing/LandingPage.module.css"),
  ]);

  assert.match(landing, /Learn with confidence\./);
  assert.match(landing, /Shape your future\./);
  assert.match(landing, /SYS_Symbol_Master_Transparent\.png/);
  assert.match(landing, /styles\.learningScene/);
  assert.match(landing, /styles\.glassDisplay/);
  assert.match(landing, /Personalized/);
  assert.match(landing, /Assessment/);
  assert.match(landing, /Progress/);
  assert.doesNotMatch(landing, /styles\.orbitSystem/);
  assert.match(styles, /@keyframes displayFloat/);
  assert.match(styles, /perspective: 1100px/);
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(styles, /animation: none !important/);
});

test("shared and landing footers carry copyright and development credit", async () => {
  const [landing, footer] = await Promise.all([
    read("../components/landing/LandingPage.js"),
    read("../components/layout/SYSFooter.js"),
  ]);

  for (const source of [landing, footer]) {
    assert.match(source, /All rights\s+reserved/);
    assert.match(source, /Conceived and developed by/);
    assert.match(source, /Dr\. Sudhakar Bolleddu/);
  }
});

test("student, faculty and administrator workspaces render the shared footer", async () => {
  const [layout, adminShell] = await Promise.all([
    read("../components/Layout.js"),
    read("../components/admin/AdminShell.js"),
  ]);

  assert.match(layout, /<RoleWorkspaceShell[\s\S]*<SYSFooter session=\{session\}/);
  assert.match(adminShell, /import SYSFooter/);
  assert.match(adminShell, /<SYSFooter session=\{\{ status: "authenticated", user \}\} \/>/);
});
