# P0-002 — Secrets & Configuration Hardening

**Task ID:** P0-002  
**Date:** 2026-08-11  
**Status:** Implemented (pending owner review/commit)

---

## Problem identified

After history cleanup and credential rotation, the working tree still had secrets-configuration gaps:

1. `backend/alembic.ini` contained a hardcoded PostgreSQL/Supabase connection string (credentials in a tracked file).
2. Alembic `env.py` read the DB URL only from `alembic.ini`, not from the environment.
3. Backend config was ad hoc (`os.getenv` / `load_dotenv` in multiple modules) with an unsafe JWT `SECRET_KEY` code fallback.
4. `.env.example` listed many unused speculative variables.
5. `.gitignore` lacked some secret/key patterns (`secrets/`, `*.pem`, etc.).
6. No local secret-scanning configuration existed in the repository.

---

## Security changes made

1. Added `backend/app/config.py` — thin dotenv-based settings object (`settings.DATABASE_URL`, `settings.SECRET_KEY`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES`). No new settings framework.
2. Updated `backend/app/database.py` to use `settings.DATABASE_URL` only.
3. Updated `backend/app/utils.py` to use `settings.SECRET_KEY` / token lifetime (no hardcoded secret fallback).
4. Replaced `backend/alembic.ini` `sqlalchemy.url` with a non-secret placeholder; documented that runtime URL comes from env.
5. Updated `backend/alembic/env.py` to load dotenv files and **require** `DATABASE_URL` before configuring Alembic.
6. Reconciled `.env.example` to variables actually used (plus documented optional frontend API URL).
7. Hardened `.gitignore` for env/secret/key/build artifacts.
8. Added `.gitleaks.toml` for local secret scanning.
9. Confirmed GitHub secret scanning + push protection are already enabled on the public repo (manual settings documented below).

---

## Configuration architecture

```text
Application (FastAPI routes, utils, database)
    ↓
backend/app/config.py  (settings)
    ↓
Environment variables  (.env / backend/.env / process env)
    ↓
DATABASE_URL / SECRET_KEY / ACCESS_TOKEN_EXPIRE_MINUTES
    ↓
SQLAlchemy engine (database.py)
Alembic migrations (alembic/env.py overrides sqlalchemy.url)
```

---

## Environment variables

| Variable | Required | Consumer | Notes |
| -------- | -------- | -------- | ----- |
| `DATABASE_URL` | Yes | `config` → SQLAlchemy + Alembic | Placeholder only in `.env.example` |
| `SECRET_KEY` | Yes | `config` → JWT utils | Use a strong random value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `config` → JWT utils | Default `30` |
| `REACT_APP_API_URL` | No | frontend `src/api.js` | Optional; code has localhost fallback |

---

## Local setup

```powershell
# From repository root
copy .env.example backend\.env
# Edit backend\.env — set real DATABASE_URL and SECRET_KEY (never commit)

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
# Note: face-recognition may fail/hang on Windows (dlib). Core API deps:
# pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary "passlib[bcrypt]" bcrypt "python-jose[cryptography]" email-validator python-multipart python-dotenv

# Backend (from backend/)
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Migrations (from backend/, requires DATABASE_URL)
alembic upgrade head

# Frontend
cd ..\frontend
npm ci
npm run dev
```

---

## Production configuration principles

1. Inject `DATABASE_URL` and `SECRET_KEY` via the host/platform secret store — never files in Git.
2. Use different secrets per environment (dev / pilot / production).
3. Rotate credentials if exposure is suspected.
4. Keep `alembic.ini` free of real URLs forever.
5. Prefer platform secret scanning + local `gitleaks detect` before push.

---

## Secret scanning

**Tool:** Gitleaks (established; not a custom scanner)

**Why:** Prevent re-introduction of credentials after the history cleanup.

**Install:**

```powershell
winget install gitleaks
# or download from https://github.com/gitleaks/gitleaks/releases
```

**Run:**

```powershell
gitleaks detect --source . --config .gitleaks.toml --verbose
```

**Exclusions:** default gitleaks rules extended; allowlist covers documented placeholders (`YOUR_PASSWORD`, `CHANGE_ME`, etc.) and cursor task docs paths.

---

## GitHub protection recommendations

Repository `drbsudhakar-ai/sys-ai-powered-learning-system` (public) was checked via GitHub API:

| Setting | Status |
| ------- | ------ |
| Secret scanning | **Enabled** |
| Push protection | **Enabled** |
| Secret scanning non-provider patterns | Disabled (optional to enable) |
| Validity checks | Disabled (optional) |

Manual path if settings ever need re-checking:

```text
GitHub repo → Settings → Code security and analysis
  → Secret scanning → Enable
  → Push protection → Enable
```

Do not disable these settings.

---

## Verification results

Executed during P0-002 implementation (2026-08-11):

| Check | Result |
| ----- | ------ |
| Config module loads `DATABASE_URL` / `SECRET_KEY` from env | **PASS** (values not logged) |
| Fail-closed when required env missing | **PASS** (`RuntimeError`) |
| Backend `from app.main import app` + routes | **PASS** (23 routes; `/` and `/auth/login` present) |
| Uvicorn health `GET /` | **PASS** (HTTP 200) |
| `alembic.ini` parseable; URL is placeholder only | **PASS** |
| Working-tree credential heuristic (source/config) | **PASS** (0 unsafe connection strings) |
| Gitleaks `detect --source . --config .gitleaks.toml` | **PASS** (`no leaks found`, exit 0) |
| Hardcoded DB passwords in working-tree config | **0** |
| GitHub secret scanning / push protection | **Already enabled** on `origin` |

Notes:
- Full `gitleaks detect --no-git` over the filesystem hits false positives inside ignored `.next` caches and vendored `exam-prep_files` assets; those paths are allowlisted. Prefer the Git-tracked scan command above for pre-commit checks.
- `backend/.env` remains local/gitignored and was not scanned into documentation.

---

## Remaining issues (out of P0-002 scope)

- Auth model field mismatch (`password` vs `hashed_password`) from earlier audit.
- Spec vs prototype API/schema drift.
- `face-recognition` / dlib install friction on Windows.
- Frontend still uses `REACT_APP_API_URL` rather than `NEXT_PUBLIC_*`.
- Until this change set is committed, `origin/main` tip may still contain the pre-fix `alembic.ini` connection string in Git; commit/push (non-force) after review.
