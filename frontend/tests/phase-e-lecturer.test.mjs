import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read = (name) => readFileSync(new URL(`../${name}`, import.meta.url), "utf8");

test("classroom has real narration, history, roster and recap controls", () => {
  const page = read("pages/learning-sessions/[id]/lecture.js");
  for (const word of ["LectureVoice", "ClassroomRoster", "getLectureQuestions", "visited_step_indices", "can_complete", "lesson_completed", "lecture.recap", "requestFullscreen"]) assert.ok(page.includes(word), word);
  assert.doesNotMatch(page, /<Layout|<RoleWorkspaceShell/);
});
test("device speech is opt-in, cancellable and has a text fallback", () => {
  const voice = read("components/lecture/LectureVoice.js");
  assert.match(voice, /useState\(false\)/);
  assert.match(voice, /SpeechSynthesisUtterance/);
  assert.match(voice, /synth.cancel\(\)/);
  assert.match(voice, /transcript remains available/);
  assert.doesNotMatch(voice, /api_key|fetch\(|axios/);
});
test("questions survive failed requests and cannot exceed the backend length", () => {
  const panel = read("components/lecture/AskLecturerPanel.js");
  assert.match(panel, /maxLength=\{2000\}/);
  assert.match(panel, /if \(succeeded\) setMessage/);
});
test("faculty invitation is distinct from student completion", () => {
  const roster = read("components/lecture/ClassroomRoster.js");
  assert.match(roster, /inviteLectureLearner/);
  assert.match(roster, /does not mark attendance or learning completion/);
  assert.match(roster, /closed/);
  assert.doesNotMatch(roster, /lectureControl/);
});
test("generated flow labels render as React text, not executable markup", () => {
  const board = read("components/lecture/DigitalTeachingBoard.js");
  assert.match(board, /t === "flow"/);
  assert.doesNotMatch(board, /dangerouslySetInnerHTML|eval\(/);
});
