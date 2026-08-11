# P0-001 — Repository, Dependency & Configuration Baseline Audit

**Task ID:** P0-001  
**Date:** 2026-08-11  
**Branch:** `main` (tracking `origin/main`)  
**Remote:** `https://github.com/drbsudhakar-ai/sys-ai-powered-learning-system`  
**Scope:** Inspection + controlled stabilization only. No feature work. No commit/push by the agent.

---

## Executive summary

The repository is a dual-app SYS prototype with `frontend/` (Next.js 16 + React 18, JavaScript Pages Router) and `backend/` (FastAPI + SQLAlchemy + Alembic + PostgreSQL/Supabase). Specification documents exist under `docs/00_project_baselines/` as `.docx` files.

A **production database credential was found hardcoded in tracked `backend/alembic.ini` and is already present on GitHub history**. The working tree was remediated to load `DATABASE_URL` from the environment. **The credential must be rotated immediately.** Git history was not rewritten.

Missing declared auth/migration packages were added. Broken frontend API imports and Next.js public env naming were corrected. Frontend `npm run build` succeeds. Backend imports and uvicorn health check succeed when `DATABASE_URL` is available via `backend/.env`. Full `pip install -r requirements.txt` on Windows hangs while building `dlib` for unused `face-recognition`.

---

## A. Actual repository structure

### EXISTING (pre–P0-001)

```text
D:\sys-ai-powered-learning-system\
├── .env.example
├── .gitignore
├── README.md                          (empty)
├── backend/
│   ├── .env                           (local only; gitignored — NOT tracked)
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── README
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── d1602d68988d_create_sys_ai_lecturer_system_tables.py
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── utils.py
│       ├── routes/
│       │   ├── auth.py
│       │   ├── courses.py
│       │   ├── assessments.py
│       │   └── resources.py
│       └── services/                  (empty directory)
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.mjs
│   ├── tailwind.config.js
│   ├── components/
│   ├── pages/                         (Pages Router; no App Router)
│   ├── public/                        (includes large exam-prep_files asset dump)
│   ├── src/api.js
│   └── styles/
└── docs/
    ├── 00_project_baselines/          (SYS .docx specs + branding zip)
    └── cursor/tasks/
        └── P0-001_REPOSITORY_DEPENDENCY_CONFIGURATION_STABILIZATION.md
```

Local/generated (present on disk, not tracked): `frontend/node_modules/`, `frontend/.next/`, `backend/**/__pycache__/`, `backend/.env`.

### CREATED BY P0-001

```text
docs/01_codebase_audit/
docs/01_codebase_audit/P0-001_BASELINE_AUDIT.md
.venv/                                 (local venv for verification; gitignored)
```

### Specification documents (present)

| Document | Location |
| -------- | -------- |
| Total Project Description & Roadmap v1.0 | `docs/00_project_baselines/SYS_Total_Project_Description_Roadmap_v1.0.docx` |
| Technology Specification v1.0 | `docs/00_project_baselines/SYS_Technology_Specification_v1.0.docx` |
| Database Model Specification v1.1 | `docs/00_project_baselines/SYS_Database_Model_Specification_v1.1.docx` |
| Backend API Specification v1.0 | `docs/00_project_baselines/SYS_Backend_API_Specification_v1.0.docx` |
| Frontend Specification v1.0 | `docs/00_project_baselines/SYS_Frontend_Specification_v1.0.docx` |
| Branding Asset Family | `docs/00_project_baselines/SYS_Branding_Asset_Family.docx` (+ zip bundle) |

---

## B. Backend technology

| Item | Actual |
| ---- | ------ |
| Runtime observed | Python 3.10.11 (host) |
| Spec recommendation | Python 3.12+ (Technology Specification) — **gap** |
| Framework | FastAPI 0.115.0 |
| ASGI server | Uvicorn 0.30.0 |
| ORM | SQLAlchemy 2.0.32 |
| Validation | Pydantic 2.x (via FastAPI; observed 2.13.4 in venv) |
| Migrations | Alembic 1.13.2 (now declared); migration revision present |
| DB driver | `psycopg2-binary` 2.9.9 |
| Database | PostgreSQL via Supabase (`DATABASE_URL`) |
| Password hashing | `passlib[bcrypt]` + `bcrypt` (code imports passlib) |
| JWT | `python-jose` (HS256); `SECRET_KEY` + `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Config | `python-dotenv` + `os.getenv` (no pydantic BaseSettings class) |
| Dependency mechanism | `backend/requirements.txt` only (no Poetry/Pipenv/pyproject) |

### Runtime schema creation

`backend/app/main.py` calls:

```python
models.Base.metadata.create_all(bind=database.engine)
```

Alembic exists in parallel. **Not redesigned in P0-001.**

### Auth libraries (configuration understanding only)

- `fastapi.security.OAuth2PasswordBearer` / `OAuth2PasswordRequestForm`
- `passlib.context.CryptContext(schemes=["bcrypt"])`
- `jose.jwt` HS256 tokens
- Hardcoded CORS origins in `main.py` (not env-driven)
- Spec prefers Supabase/JWT-compatible auth under `/api/v1` — **code/spec conflict; not redesigned**

---

## C. Frontend technology

| Item | Actual |
| ---- | ------ |
| Node.js observed | v24.14.0 |
| Package manager | npm (`package-lock.json` lockfileVersion 3) |
| Framework | Next.js 16.3.0 (Pages Router) |
| UI | React 18.2.0 / react-dom 18.2.0 |
| Language | **JavaScript** (no `tsconfig.json`; no TypeScript sources) |
| Spec recommendation | Next.js + React + **TypeScript** — **gap** |
| Styling | Tailwind CSS 4.x + PostCSS (`@tailwindcss/postcss`) |
| HTTP client | axios ^1.6.0 |
| Icons | `@heroicons/react` ^2.2.0 |
| `next.config.*` | **Not present** |
| Scripts | `dev`, `build`, `start`, `lint` |

---

## D. Environment variables

Variables actually consumed by code (after P0-001 alignment):

| Variable | Consumer | Required | Default/Example | Secret? |
| -------- | -------- | -------- | --------------- | ------- |
| `DATABASE_URL` | backend `database.py`, Alembic `env.py` | Yes (backend raises if missing) | empty in `.env.example` | Yes |
| `SECRET_KEY` | backend `utils.py` | Strongly yes | code fallback `"supersecretkey"` (unsafe) | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend `utils.py` | No | `30` | No |
| `NEXT_PUBLIC_API_BASE_URL` | frontend `src/api.js` | No | `http://127.0.0.1:8000` | No (public) |

Local `backend/.env` (gitignored) currently defines: `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (values not recorded here).

### Removed from `.env.example` as not consumed by current code

Speculative template entries such as `APP_NAME`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, AI provider keys, SMTP, storage, `TEST_DATABASE_URL`, etc. were not referenced by the current application source. They were removed from the template to avoid false confidence. Reintroduce only when code actually consumes them.

### Hardcoded configuration (not env)

| Setting | Location |
| ------- | -------- |
| CORS origins | `backend/app/main.py` |
| JWT algorithm `HS256` | `backend/app/utils.py` |
| FastAPI title/description | `backend/app/main.py` |

---

## E. Dependency findings

| Component | Finding | Severity | Action |
| --------- | ------- | -------- | ------ |
| Backend | `passlib`, `python-jose`, `alembic` imported/used but previously undeclared | High | **Fixed** — added to `requirements.txt` |
| Backend | `face-recognition`, `opencv-python`, `pandas`, `firebase-admin`, `requests` declared but not imported by current app modules | Medium | Documented; not removed (may be intended for later). Full install builds `dlib` and can hang on Windows |
| Backend | Auth code uses `user.password` / `password=` while model column is `hashed_password` | High | **Unresolved** — deferred (auth redesign out of scope) |
| Backend | Course routes reference `duration`/`category` fields not aligned with current `Course` model | High | **Unresolved** — deferred to DB/API reconciliation |
| Frontend | Pages imported `../api` but module lives at `src/api.js` | High | **Fixed** — imports → `../src/api` |
| Frontend | Used `REACT_APP_API_URL` in Next.js (not exposed) | Medium | **Fixed** — `NEXT_PUBLIC_API_BASE_URL` |
| Frontend | `eslint@10` peer conflict with `eslint-config-next` / `eslint-plugin-react` expecting eslint ≤9 | Low | Documented; no major upgrade in P0-001 |
| Frontend | `npm run lint` fails on Next 16 (`next lint` treated as directory) | Medium | Documented baseline; no lint redesign |
| Lockfile | `package-lock.json` present and used via `npm ci` | Info | Prefer `npm ci` |

---

## F. Configuration findings

| File | Finding | Severity | Action |
| ---- | ------- | -------- | ------ |
| `backend/alembic.ini` | Contained hardcoded live DB URL/credentials in Git | Critical | **Remediated** — placeholder URL; runtime from `DATABASE_URL` |
| `backend/alembic/env.py` | Read URL only from ini | Critical | **Fixed** — loads dotenv + `DATABASE_URL` |
| `backend/app/database.py` / `utils.py` | `load_dotenv()` cwd-only | Medium | **Fixed** — also loads `backend/.env` |
| `.env.example` | Contained many unused vars; mismatched frontend env name | Medium | **Reconciled** to actual consumers |
| `.gitignore` | Missing several build/coverage/key patterns | Low | **Expanded** |
| `backend/app/main.py` | Uses `create_all` at import/startup | Medium | Documented only |
| Spec vs code | Spec `/api/v1` + UUID IDs + Supabase auth vs prototype `/auth` etc. | High | Documented; no contract rewrite in P0-001 |
| Spec vs code | Branding: orange Tailwind brand vs Blue/Royal Purple brand docs | Medium | Documented; no UI redesign |
| `README.md` | Empty | Low | Not rewritten in P0-001 |

---

## G. Security findings

| Finding | Location | Severity | Action |
| ------- | -------- | -------- | ------ |
| Hardcoded database credential in tracked config | `backend/alembic.ini` (also in Git history / GitHub) | **Critical** | Removed from working tree; env-based config; **ROTATE CREDENTIAL NOW** |
| Credential likely already exposed on remote | Commit `20e4824` on `origin/main` | **Critical** | Report only — **do not rewrite history automatically**; rotate DB password / revoke compromised credentials |
| Local `backend/.env` present | Disk only; gitignored | Info | Keep untracked; verify never force-added |
| Unsafe JWT fallback `SECRET_KEY` default | `backend/app/utils.py` | High | Documented; changing auth defaults deferred |
| `NEXT_PUBLIC_*` used only for API base URL | frontend | Info | No private secrets in public vars |
| Large third-party `exam-prep_files` dump in `frontend/public` | tracked assets | Low | Review separately for licensing/size; not secret |

**Never print credential values in this report.**

**Owner action required:** Rotate the Supabase/PostgreSQL password that was previously embedded in `alembic.ini`, update all local `.env` files, and treat the old secret as compromised. Consider history scrubbing only as a deliberate follow-up with the owner.

---

## H. Build/startup results

### Backend

```text
Command: python -m venv .venv && pip install <core declared deps excluding face-recognition build>
Result: Success for core runtime stack (fastapi/uvicorn/sqlalchemy/alembic/passlib/jose/dotenv/psycopg2)
Status: PASS (core) / BLOCKED (full requirements.txt on this Windows host due to dlib/cmake build hang for face-recognition)

Command: python -c "from app.main import app" (cwd=backend, with backend/.env)
Result: IMPORT_OK; title "SYS AI Lecturer System"; 23 routes discovered including /auth/*, /courses/*, /assessments/*, /resources/*, /
Status: PASS

Command: uvicorn app.main:app --host 127.0.0.1 --port 8000
Result: GET / -> 200 {"message":"SYS AI Lecturer Backend is running"}; OpenAPI paths discoverable
Status: PASS (requires valid DATABASE_URL; create_all runs at startup)
```

### Frontend

```text
Command: npm ci (cwd=frontend)
Result: 354 packages; peer dependency warnings for eslint 10 vs eslint-plugin-react
Status: PASS (with warnings)

Command: npm run build
Result: Next.js 16.3.0 compiled successfully; 14 static pages generated
Status: PASS

Command: npm run lint
Result: Invalid project directory .../frontend/lint
Status: FAIL (tooling baseline issue under Next 16 CLI behavior)
```

---

## I. Test baseline

| Area | Present? | Result |
| ---- | -------- | ------ |
| Backend unit/integration/API tests | No | NOT APPLICABLE |
| Frontend unit/component tests | No | NOT APPLICABLE |
| E2E (Playwright etc.) | No | NOT APPLICABLE |
| pytest / coverage config | No | NOT APPLICABLE |
| ESLint via `npm run lint` | Script exists | FAIL (see above) |
| Typecheck | No TypeScript project | NOT APPLICABLE |

Spec recommends pytest + Playwright; not implemented yet. P0-001 did not create a new test framework.

---

## J. Changes made

1. Removed hardcoded DB credentials from `backend/alembic.ini`; documented env override.
2. Updated `backend/alembic/env.py` to load dotenv and set `sqlalchemy.url` from `DATABASE_URL`.
3. Updated `backend/app/database.py` and `backend/app/utils.py` to load `backend/.env` reliably.
4. Declared missing packages in `backend/requirements.txt`: `alembic`, `passlib[bcrypt]`, `python-jose[cryptography]`.
5. Fixed frontend API import paths in `login.js`, `register.js`, `dashboard.js`.
6. Aligned frontend env var to `NEXT_PUBLIC_API_BASE_URL` in `src/api.js`.
7. Reconciled `.env.example` to variables actually consumed.
8. Expanded `.gitignore` for build/coverage/key/storage artifacts.
9. Created this audit report under `docs/01_codebase_audit/`.

---

## K. Unresolved issues

1. **Credential rotation / exposure on GitHub** — working tree fixed; history still contains secret.
2. **Auth model field mismatch** (`password` vs `hashed_password`) — register/login likely broken at runtime.
3. **Schema/API drift** vs Database Model v1.1 and Backend API Spec v1.0 (prefix `/api/v1`, UUID IDs, richer academic hierarchy, Supabase auth).
4. **`create_all` vs Alembic** dual initialization strategy.
5. **Course route/model field mismatch** (`duration`/`category`).
6. **TypeScript / Python 3.12 gaps** vs Technology Specification.
7. **Unused heavy deps** (`face-recognition` et al.) blocking clean Windows installs.
8. **`npm run lint` broken** under current Next 16 script behavior.
9. **Empty `README.md`** and empty `backend/app/services/`.
10. **Brand color mismatch** (frontend orange vs brand Blue/Royal Purple).
11. **Authoritative specs conflict with prototype code** — architectural alignment deferred to later tasks (stop condition honored; no silent redesign).

---

## L. Recommended next task

**Immediate (ops, before further cloud work):** Rotate the exposed Supabase database credentials and confirm no other secrets remain in Git history.

**Next engineering task (based on findings):** Database & schema reconciliation against `SYS_Database_Model_Specification_v1.1.docx`, including retirement of unsafe `create_all` assumptions and alignment of Alembic migrations — **before** API contract or auth redesign. Auth field bugs and `/api/v1` contract alignment should follow immediately after schema baseline is clear.

Do not assume a numbered task ID unless the project execution plan defines one; prioritize secret rotation, then DB reconciliation.

---

## Acceptance criteria checklist

| Criterion | Status |
| --------- | ------ |
| Repository inspected as it actually exists | PASS |
| Specs located and acknowledged (not invented) | PASS |
| Backend/frontend tech & deps inventoried | PASS |
| Env vars inventoried; `.env.example` reconciled | PASS |
| Secrets audit performed; tracked secret remediated in working tree | PASS |
| Exposed remote credential reported; history not rewritten | PASS |
| `.gitignore` / node_modules policy verified | PASS |
| Backend install/import/startup verified as far as practical | PASS (core) / BLOCKED (full face-recognition install on Windows) |
| Frontend `npm ci` + build verified | PASS |
| Test baseline documented | PASS |
| Audit report created | PASS |
| No architecture/feature redesign performed | PASS |
| No commit/push by agent | PASS |

---

## Recommended Git commands for the project owner

```bash
# Review changes
git status
git diff

# After rotating the database password and updating local backend/.env:
git add .gitignore .env.example backend/alembic.ini backend/alembic/env.py backend/app/database.py backend/app/utils.py backend/requirements.txt frontend/src/api.js frontend/pages/login.js frontend/pages/register.js frontend/pages/dashboard.js docs/01_codebase_audit/P0-001_BASELINE_AUDIT.md

git commit -m "$(cat <<'EOF'
fix: stabilize repo baseline and remove tracked DB credentials

Align env templates and dependency declarations with the current
codebase, and load Alembic/SQLAlchemy URLs from DATABASE_URL only.
EOF
)"

# Push only when ready (does not remove secret from prior commits)
git push origin HEAD

# Separately plan credential rotation + optional history scrub with owner approval
```

**Stop.** P0-001 complete per inspect → analyze → stabilize → test → document → stop.
