# SYS Phase E — AI Lecturer pilot

This incremental patch applies after `SYS_AI_Provider_Administration_and_Usage.patch`.
It has no database migration and does not replace the existing learning-session,
enrollment, assessment, performance, or remedial infrastructure.

## Implemented behavior

- Live topic/subtopic lesson plans are generated through the configured SYS gateway.
  Syllabus descriptions, objectives, unit/subtopic names, and configured topic
  weightage are passed as academic context. No student identity is passed for plans.
- Provider output is a strict data contract: 3–8 teaching stages, board text,
  optional bullets/formula/process flow, narration, and only two predefined 3D
  schematic types. Model-authored HTML, JavaScript, URLs and arbitrary 3D names
  are rejected and never executed.
- Common/hybrid lessons must first be prepared by authorized faculty/admin. This
  makes one saved plan reusable by invited learners and avoids one generation call
  per student. Individual sessions allow the assigned enrolled learner to prepare
  their lesson. Existing saved template lessons remain reusable.
- Faculty classroom roster lists active course enrollments with minimal identity
  fields and supports selecting/inviting learners. Invitation does not mark
  attendance, progress or completion.
- Projector mode uses browser fullscreen for an in-room, faculty-led common class.
  The facilitator can end the session; this saves the common session end timestamp
  without marking every learner complete. This release does not broadcast controls
  in real time to remote student devices.
- Opt-in narration uses available browser/device speech synthesis. It makes no
  Groq request and provides transcript fallback. Availability, accents and whether
  a browser uses local or network speech services depend on the device/browser.
  It is not voice cloning or a photorealistic avatar.
- Student questions, requests for examples/visual explanations, and explanations
  use the configured gateway. Free text is disclosed as external-provider content,
  limited to 2,000 characters, saved in the learner's evidence, and visible in the
  learner's private history. Personal answers are not appended to the common plan.
- Every stage visit is append-only learning evidence. Completion requires visiting
  every plan stage and reviewing the recap. Completion is idempotent. It completes
  the lecture activity only; other tasks, topic mastery, assessment performance and
  other students remain independent.
- Course coordinators retain course scope; subject experts can manage only assigned
  subjects. Enrollment and published-course access are still enforced.

## Apply from the repository root

```powershell
git apply --check "$HOME\Downloads\SYS_Phase_E_AI_Lecturer_Integration.patch"
git apply "$HOME\Downloads\SYS_Phase_E_AI_Lecturer_Integration.patch"
```

No Alembic command is required for this incremental patch.

## Verify backend

```powershell
cd backend
$env:TEST_DATABASE_URL = "sqlite:///:memory:"
python -m unittest `
  tests.test_ai_management `
  tests.test_ai_lecturer `
  tests.test_phase_d_workspace `
  tests.test_learning_session_api `
  tests.test_learning_session_behavior `
  -v
```

## Verify frontend

```powershell
cd ..\frontend
node --test `
  tests/phase-e-lecturer.test.mjs `
  tests/ai-provider.test.mjs `
  tests/phase-d-workspace.test.mjs
npm run test:frontend
npm run build
```

Restart both applications after applying.

## Pilot walkthrough

1. As faculty, open the pilot course workspace and choose one approved syllabus
   topic. Select **Manage sessions**, create a Common classroom, and enter it.
2. The first faculty open generates and saves one plan. Do not refresh while the
   request is running. If the provider fails, use **Retry opening classroom**;
   SYS does not silently substitute mock output.
3. Review every stage and factual claim before presenting. Use **Projector mode**,
   opt into a suitable device voice, and invite the enrolled pilot learners.
4. As one invited student, enter the session, navigate stages, ask one question,
   review private history and recap, then complete the lesson.
5. As another student, verify the first learner's question is absent. As faculty,
   end the common session and verify this did not mark all students complete.
6. Check **Admin → AI Provider & Usage** for `TEACHING_PLAN` and interaction events.
   Reopening the saved common plan and ordinary navigation should not add AI usage.

For the first Groq lesson, the existing 1,500 output-token cap may be sufficient
for a compact topic. If the provider returns a truncated/invalid lesson contract,
raise **Maximum output tokens per request** to 2,000–2,500 only after confirming
that the rolling-minute and daily budgets leave adequate headroom. Each failed
provider request may still count against Groq's quota.

## Boundaries for the pilot

- AI content is labelled unreviewed and is not a source of official current-affairs
  truth, exam rules or assessment scores. Faculty review is mandatory.
- The 3D display is a controlled schematic component library, not generated 3D
  video. Add new reviewed visual components through code; never execute a model's
  code or load an arbitrary model URL.
- Browser narration is the no-additional-provider pilot option. A professional
  server TTS provider, pronunciation controls and audio caching require a separate
  provider adapter and administration/usage policy.
- A photorealistic avatar, lip synchronization, multilingual translation, remote
  classroom control broadcast, faculty approval/version history for generated
  lessons, citation-backed retrieval, and downloadable recaps are not represented
  as completed by this patch.
- Phase F remains responsible for assessment launch, results, answer explanations,
  performance monitoring, learning-gap identification and remedial recommendations.
