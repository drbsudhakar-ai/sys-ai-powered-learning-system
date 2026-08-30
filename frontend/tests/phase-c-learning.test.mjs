import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("published course topics launch the existing AI lecturer classroom", async () => {
  const api = await read("../src/api.js");
  const workspace = await read("../pages/courses/[id]/workspace.js");
  assert.match(api, /learning\/topics\/\$\{topicId\}\/launch/);
  assert.match(workspace, /launchCourseTopicLearning/);
  assert.match(workspace, /Start AI lesson/);
  assert.match(workspace, /Resume AI lesson/);
});

test("classroom is SYS branded and keeps the full teaching control set", async () => {
  const classroom = await read("../pages/learning-sessions/[id]/lecture.js");
  const css = await read("../components/lecture/AILecturerClassroom.module.css");
  assert.match(classroom, /SYS — STRENGTHEN YOUR SKILLS/);
  assert.match(classroom, /Lesson stages/);
  assert.match(classroom, /AskLecturerPanel/);
  assert.match(classroom, /LectureControls/);
  assert.match(css, /linear-gradient/);
  assert.match(css, /\.digital-board/);
});

test("faculty planner supports all agreed learning modes", async () => {
  const sessions = await read("../pages/learning-sessions/index.js");
  assert.match(sessions, /Common classroom/);
  assert.match(sessions, /Hybrid classroom/);
  assert.match(sessions, /Individual learning/);
  assert.match(sessions, /primary_student_id/);
});
