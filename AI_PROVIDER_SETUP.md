# SYS AI provider administration — pilot setup

This incremental patch is based on the supplied source with the Pending Enrollment
and Phase D Student Learning Workspace patches applied. Back up your repository
and database first. Do not force-apply if `git apply --check` reports a conflict.

## What this implements

- Administrator navigation: **AI Administration → AI Provider & Usage**.
- Page: `/admin/ai-provider`; backend routes: `/admin/ai/provider`,
  `/admin/ai/provider/test`, `/admin/ai/usage`.
- One active, changeable configuration: protocol, endpoint, model and credential.
- Hosted OpenAI-compatible JSON chat APIs (including Groq) and an Ollama adapter.
- Encrypted API keys, admin-only access, redacted validation/errors, revision-safe
  settings updates, audit entries, and server-approved endpoints.
- Shared daily/rolling-minute request and token budgets, and a per-student daily
  live-request allowance. Reservations are serialized across backend workers using
  the database. No automatic retries or silent fallback to mock lessons.
- Daily UTC request totals, provider-reported versus estimated tokens, failures,
  purpose breakdown, usage by account (top 100), and the latest 50 requests.
- Existing AI Lecturer consumes validated generated lesson text and explanations.
  Shared saved lessons are reused; playback/navigation do not call the provider.
  Personal live explanations are shown in the current response and recorded in
  participant evidence, not appended to the shared classroom plan. They do not
  become extra shared syllabus steps. Faculty/admin session evidence permissions
  continue to apply.

“Provider independent” means orchestration does not depend on a vendor SDK.
It does not mean every vendor has the same HTTP protocol. Providers with proprietary
formats require an additional adapter. Models must support the selected JSON chat
contract. Unsupported parameters/invalid JSON fail explicitly and may consume quota.

## 1. Apply from repository root (PowerShell)

```powershell
git apply --check "$HOME\Downloads\SYS_AI_Provider_Administration_and_Usage.patch"
git apply "$HOME\Downloads\SYS_AI_Provider_Administration_and_Usage.patch"
cd backend
python -m pip install -r requirements-ai.txt
```

Install these alongside, not instead of, your existing backend dependencies.

## 2. Set server-owned encryption and endpoint configuration

Generate the encryption key ONCE in your backend environment:

```powershell
$env:SYS_AI_ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$env:SYS_AI_PROVIDER = "configured"
```

The command sets the current PowerShell process environment. Persist the same key
in your deployment secret store or the existing, untracked backend `.env` before
closing that terminal. All workers must use the same key. Keep a secure backup.
Never commit it, put it in `NEXT_PUBLIC_*`, or paste it into chat. Do not regenerate
it on every startup. Losing/changing it requires re-entering the provider API key.

Optional backend-only variables:

```text
SYS_AI_PROVIDER=configured
SYS_AI_ALLOWED_BASE_URLS=https://api.groq.com/openai/v1,https://api.openai.com/v1,https://openrouter.ai/api/v1
SYS_AI_OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Use only operator-trusted endpoints. An approved endpoint receives the saved key
and academic prompts. Hosted URLs require HTTPS; redirects and environment proxies
are disabled. Local Ollama HTTP is intended for loopback/private deployment only;
use TLS and an authenticated gateway if it crosses an untrusted network. If a
deployment requires an outbound proxy, an explicit trusted proxy configuration
needs to be added; this patch intentionally does not inherit proxy variables.

Use HTTPS for SYS itself outside localhost so admin credential entry is protected.
Do not expose backend databases, Ollama, or encryption keys publicly.

## 3. Migrate and restart

With the backend stopped, back up the database and run your existing migration
workflow, normally:

```powershell
python -m alembic upgrade head
uvicorn app.main:app --reload
```

New revision: `20260827_p027_ai_gateway`, after `20260826_p026_enrollment`.
It adds only `ai_provider_settings` and `ai_usage_events`; no existing student,
course, enrollment or progress records are rewritten. The migration tolerates
these two tables already created by the application's existing startup create_all.
Do not stamp unrelated migrations to bypass an error. Restart frontend separately.

## 4. Configure the Groq pilot

Open **AI Administration → AI Provider & Usage** as administrator.

1. Select **OpenAI-compatible**, base `https://api.groq.com/openai/v1`.
2. Enter the exact currently available model ID from your Groq console. Do not
   assume a model or free-tier quota remains available indefinitely.
3. Enter the API key. Leave live AI disabled for the initial save.
4. Save, then click **Test saved connection**. The test consumes a request.
5. Review the provider's actual quotas. Set SYS limits below them with headroom.
6. Enable live AI and save. Generate one pilot topic and review it before the demo.

Initial local defaults are conservative starting controls, NOT verified Groq
entitlements: 100 requests/day, 150,000 budget tokens/day, 4 requests/minute,
7,000 budget tokens/minute, 2 requests/student/day, 1,500 maximum output tokens.
Adjust them to the model and your real quota. Long prompts may be refused even if
request counts are low. In the 25-student pilot, a new individual lesson uses one
student request and a question uses another; a saved/common lesson avoids repeated
generation. Prepare shared demonstrations in advance to reduce burst demand.

The settings page controls application requests, not student account capacity.
Institutional users, course management, saved MCQ scoring, learning evidence and
ordinary reports do not need an AI call. Any future AI assessment/recommendation
feature must call this gateway to be included in its budgets and usage panel.

## Usage semantics and limitations

- UTC daily budgets reset at midnight; rolling-minute budgets use the last 60 seconds.
- Token reservations use UTF-8 request bytes plus output allowance and overhead,
  not a vendor tokenizer. This is deliberately conservative, not exact billing.
- Provider total_tokens replaces the estimate when supplied. Missing usage and
  failures keep the reservation. An interrupted process leaves a RESERVED record;
  it remains counted through the current day rather than risking overspend.
- Provider quotas are shared with other applications using the same provider
  account. The SYS panel cannot see that external usage or guarantee free service.
- No monetary cost is shown. Requests returned as valid JSON can still fail lesson
  schema validation; provider usage remains counted. SUCCEEDED means JSON API
  success, not factual accuracy or faculty approval.
- Disabling AI stops new generation, not already admitted requests. Saved lessons
  remain readable. Changing providers does not reset the day's accumulated usage.
- Gateway records contain no prompts, answers or keys. Normal learning evidence
  stores learner questions/explanations under existing session permissions.
- AI-generated material is labelled, not automatically approved. Faculty must check
  exam facts, current affairs, numerical answers and the syllabus against authoritative
  sources. This patch does not add retrieval/citations or a formal approval queue.
- This is text/JSON provider integration. It retains the existing narration and
  classroom infrastructure; it does not add photorealistic avatars, generated 3D
  scenes, paid speech synthesis, or a new voice provider configuration.
- Live personal explanations appear immediately and are retained as evidence.
  A dedicated Q&A history/replay interface is not added here.
- Use `SYS_AI_PROVIDER=mock` or `echo` only for explicitly labelled offline
  development. Default is `configured`; with no saved config, generation returns
  a clear setup error. Never present mock output as live AI.

## Verification

Keep your normal DATABASE_URL configured; the test harness isolates the database
using TEST_DATABASE_URL. Do not point tests at a live database.

```powershell
cd backend
$env:TEST_DATABASE_URL = "sqlite:///:memory:"
python -m unittest tests.test_ai_management tests.test_ai_lecturer tests.test_phase_d_workspace tests.test_pending_enrollment tests.test_courses -v
cd ..\frontend
node --test tests/ai-provider.test.mjs
npm run test:frontend
npm run build
```

The supplied source subset supports focused backend tests and frontend source
checks. A full Next production build and visual browser review must be performed
in your complete repository. Provider HTTP responses in automated tests are
simulated; a real Groq/Ollama connection requires your configured service.

Before presenting: verify admin save/test, deny student/faculty access to settings,
prepare a shared lesson, open it as two students, ask an individual question, check
that the other learner does not see it, confirm usage increments, disable live AI,
and confirm saved lessons and progress still open. Keep the API key off projected
screens and prepare saved lesson content in case the free provider is unavailable.
