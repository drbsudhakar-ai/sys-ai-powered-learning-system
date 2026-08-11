# Cursor Task: P0-002 — Repository Secrets & Configuration Hardening

## Context

The SYS AI-Powered Learning System repository has just completed a Git history cleanup.

The previous repository history accidentally contained a Supabase PostgreSQL connection string with a database password. The Git history has been rewritten successfully, the exposed credential has been rotated, and the cleaned `main` branch has been force-pushed to GitHub.

Current repository state:

* Branch: `main`
* Git working tree: clean
* `origin/main`: synchronized with local `main`
* Previous exposed database credential: removed from Git history
* Supabase database password: rotated
* `docs/01_codebase_audit/P0-001_BASELINE_AUDIT.md`: committed

Do **not** rewrite Git history again.

Do **not** force-push anything.

Do **not** modify or delete existing project functionality unless required for secure configuration.

---

# Objective

Implement **P0-002 — Repository Secrets & Configuration Hardening**.

The objective is to ensure that:

1. No database credentials or API keys are hardcoded in source code.
2. Database configuration is loaded from environment variables.
3. `.env` files cannot accidentally be committed.
4. A safe `.env.example` is provided for developers.
5. Existing application functionality continues to work.
6. Alembic/database configuration does not contain real credentials.
7. Development and production configuration can be separated cleanly.
8. The repository has basic protection against future secret leaks.
9. The implementation is documented.
10. All changes are tested before completion.

---

# Step 1 — Inspect Before Modifying

First inspect the repository structure.

Do NOT immediately modify files.

Inspect at minimum:

```text
.gitignore
README.md
backend/
backend/app/
backend/alembic.ini
backend/app/database.py
backend/app/config/
backend/requirements.txt
pyproject.toml
.env
.env.example
```

if they exist.

Also search the repository for possible credentials:

```text
postgresql://
postgres://
DATABASE_URL
SUPABASE
API_KEY
SECRET_KEY
PASSWORD
TOKEN
PRIVATE_KEY
AWS_
OPENAI_
GEMINI_
ANTHROPIC_
```

Use appropriate exclusions for:

```text
.git/
.venv/
venv/
node_modules/
__pycache__/
```

Do not expose discovered secrets in the final report. Redact actual credential values.

---

# Step 2 — Analyze Existing Configuration

Determine:

* How the backend currently obtains the database URL.
* Whether SQLAlchemy is being used.
* How Alembic obtains its database URL.
* Whether Pydantic/Pydantic Settings is already used.
* Whether a configuration module already exists.
* Whether `.env` loading already exists.
* Whether the frontend contains environment variables.
* Whether any credentials are hardcoded.
* Whether Docker/deployment configuration exists.

Do not introduce a new configuration framework if an appropriate existing framework is already present.

Prefer the project's existing architecture.

---

# Step 3 — Secure Database Configuration

The application must not contain a real database credential in:

```text
backend/alembic.ini
backend/app/database.py
source code
documentation
README files
tests
configuration committed to Git
```

The database URL should come from:

```text
DATABASE_URL
```

Environment variable.

For example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres
```

Use a placeholder only in `.env.example`.

Never put a real password in `.env.example`.

---

# Step 4 — Update database.py

Modify the existing database configuration so that the database URL is obtained from the environment/configuration layer.

Preferred architecture:

```python
DATABASE_URL = settings.DATABASE_URL
```

or equivalent using the project's existing configuration mechanism.

Do not hardcode:

```text
postgresql://...
```

Do not hardcode:

```text
postgres...
```

Do not hardcode passwords.

Do not introduce unnecessary architectural changes.

Preserve existing SQLAlchemy engine/session behavior.

---

# Step 5 — Secure Alembic

Inspect:

```text
backend/alembic.ini
```

Remove any real database credentials.

Prefer configuring Alembic dynamically from the application's configuration.

If the current Alembic setup uses:

```ini
sqlalchemy.url = ...
```

determine the safest project-compatible approach.

If appropriate, configure Alembic's `env.py` to obtain:

```text
DATABASE_URL
```

from the application's environment/configuration.

Do not simply replace the credential with another hardcoded credential.

The final committed repository must contain no real database password.

---

# Step 6 — Environment Files

Create or update:

```text
.env.example
```

with safe placeholders.

Example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres
SECRET_KEY=CHANGE_ME
```

Only include variables actually required by the project.

Do not invent unnecessary variables.

If the project already has known variables, document them accurately.

---

# Step 7 — Harden .gitignore

Ensure `.gitignore` protects environment and secret files.

At minimum consider:

```gitignore
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
secrets/
```

Do not blindly add patterns that could hide legitimate project files.

Review the resulting `.gitignore` for correctness.

---

# Step 8 — Secret Scanning

Implement a lightweight local secret-detection mechanism.

Preferred options:

* `gitleaks`
* `detect-secrets`
* another established secret-scanning tool

Do not create a large custom security framework.

If introducing a dependency, document:

* why it is needed
* how to install it
* how to run it
* what files are excluded

Example desired command:

```text
gitleaks detect
```

or equivalent.

The scan must pass against the repository.

Do not report actual secrets in output.

---

# Step 9 — GitHub Protection

Determine whether the repository can use GitHub secret scanning / push protection.

Do not attempt to change GitHub repository settings using guessed APIs or credentials.

If configuration cannot be performed automatically, document the exact manual GitHub setting that should be enabled.

Recommended:

```text
Secret scanning
Push protection
```

---

# Step 10 — Tests

Run the project's existing test suite.

At minimum perform:

```text
backend import/startup validation
database configuration validation
Alembic configuration validation
secret scan
Git status
```

If there is a Python test suite, run the appropriate test command.

Do not weaken or remove existing tests merely to make them pass.

---

# Step 11 — Security Verification

Before completing the task, search the repository again for:

```text
SupabaseDB4882
postgresql://
postgres://
password=
PASSWORD=
SECRET_KEY=
API_KEY=
TOKEN=
```

Distinguish between:

### Safe

Examples/placeholders:

```text
postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres
```

```text
postgres:<PASSWORD>
```

### Unsafe

Actual credentials:

```text
postgresql://username:realpassword@realhost/...
```

Never include an actual secret in the final report.

---

# Step 12 — Documentation

Update:

```text
docs/01_codebase_audit/P0-001_BASELINE_AUDIT.md
```

only if appropriate, or create:

```text
docs/02_security_configuration/
```

with a concise document:

```text
P0-002_SECRETS_CONFIGURATION_HARDENING.md
```

Document:

* problem identified
* security changes made
* environment variables
* local setup
* production configuration principles
* secret scanning
* GitHub protection recommendations
* verification results

Do not include real credentials.

---

# Step 13 — Git Safety

Do NOT:

```text
git reset --hard
git filter-repo
git filter-branch
git push --force
```

This task is a normal forward commit after the already completed history cleanup.

Before finishing:

```bash
git status
```

must show only the intended changes.

Do not commit unrelated files.

---

# Deliverables

At completion provide:

## 1. Files changed

List every modified/created file.

## 2. Configuration architecture

Explain:

```text
Application
    ↓
Configuration layer
    ↓
Environment variables
    ↓
DATABASE_URL
    ↓
SQLAlchemy / Alembic
```

## 3. Security verification

Report:

```text
Real credentials found: 0
Hardcoded database passwords: 0
Secret scan: PASS
Tests: PASS/FAIL
```

Do not display actual credentials.

## 4. Developer setup

Provide the exact steps a developer should follow:

```text
copy .env.example to .env
configure DATABASE_URL
install dependencies
run backend
run migrations
```

Use the project's actual commands rather than inventing commands.

## 5. Git status

Confirm the repository has only intended changes.

## 6. Recommended commit

Suggest:

```text
security: harden repository secrets and configuration
```

Do not create the commit automatically unless explicitly instructed.

---

# Important Constraints

* Preserve existing application functionality.
* Do not redesign the application.
* Do not change database schema unless absolutely required.
* Do not introduce unnecessary dependencies.
* Do not expose secrets in logs, screenshots, documentation, or reports.
* Do not rewrite Git history.
* Do not force-push.
* Do not modify unrelated files.
* Do not claim a security scan passed unless it was actually executed.
* Do not claim tests passed unless they were actually executed.

Work methodically: **inspect → plan → modify → test → scan → report**.
