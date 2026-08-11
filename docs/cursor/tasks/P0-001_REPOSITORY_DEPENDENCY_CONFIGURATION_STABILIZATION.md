# SYS — P0-001

# Repository, Dependency & Configuration Stabilization

**Task ID:** P0-001
**Phase:** Phase 0 — Foundation
**Priority:** P0
**Status:** NOT_STARTED
**Type:** Repository Inspection + Controlled Stabilization

---

## 1. TASK OBJECTIVE

Inspect the **actual current SYS repository** and establish a reliable, reproducible, and secure development baseline for the existing frontend and backend.

This task is primarily an **inspection and stabilization task**.

It is NOT a feature-development task.

The objectives are to:

1. Understand the actual repository structure.
2. Identify the technologies and versions currently used.
3. Identify frontend and backend dependencies.
4. Identify configuration mechanisms.
5. Identify all environment variables currently consumed.
6. Identify development, build, test, and startup commands.
7. Identify configuration inconsistencies.
8. Identify missing dependencies or broken imports.
9. Identify accidentally tracked secrets or sensitive files.
10. Verify frontend and backend build/startup as far as practically possible.
11. Establish a documented baseline.
12. Make only minimal and safe stabilization changes.
13. Document all findings for subsequent SYS tasks.

---

# 2. IMPORTANT — ACTUAL REPOSITORY IS THE SOURCE FOR THIS TASK

Do NOT assume that planned SYS documentation directories or future project artifacts already exist.

At the beginning of this task, inspect the repository from its actual root:

```text
D:\sys-ai-powered-learning-system\
```

Discover what is actually present.

The repository may currently contain the existing:

```text
frontend/
backend/
```

and other files/folders.

Do NOT assume that the following directories exist:

```text
docs/01_codebase_audit/
docs/02_execution/
docs/03_phase_0/
docs/04_phase_1/
docs/cursor/
```

If they do not exist, do not attempt to read them.

---

# 3. P0-001 TASK DOCUMENT

This task is being provided through:

```text
docs/cursor/tasks/P0-001_REPOSITORY_DEPENDENCY_CONFIGURATION_STABILIZATION.md
```

Read this document first.

Then inspect the rest of the repository.

Do not assume that any other documentation, specification, roadmap, audit, or execution files exist unless they are actually present.

---

# 4. PROJECT SPECIFICATIONS

If approved SYS specification documents are present in the repository, locate and read them before making architectural decisions.

Do not assume their exact filenames or directory locations.

Search the repository for relevant project specification documents, particularly documents concerning:

* overall SYS project description and roadmap
* database model
* backend API
* frontend requirements
* technology stack
* SYS branding

If these documents are NOT present in the current repository, report:

```text
Specification documents not currently present in repository.
```

Do NOT invent their contents.

Do NOT reconstruct missing specifications from assumptions.

Do NOT create replacement specifications during P0-001.

---

# 5. INSPECTION-FIRST RULE

Before modifying source code:

1. Inspect the repository.
2. Inspect configuration.
3. Inspect dependencies.
4. Inspect environment variables.
5. Inspect startup/build/test mechanisms.
6. Identify problems.
7. Determine which problems are safe to fix within P0-001.
8. Only then make minimal stabilization changes.

Do NOT begin by rewriting or refactoring code.

---

# 6. REPOSITORY STRUCTURE AUDIT

Inspect the complete repository tree.

Identify:

```text
Root files
Frontend
Backend
Tests
Scripts
Documentation
Configuration
Assets
Generated files
Development artifacts
Other project components
```

Produce an actual repository structure summary.

Do not create a theoretical or planned structure.

Clearly distinguish:

```text
EXISTING
```

from:

```text
CREATED BY P0-001
```

---

# 7. BACKEND INSPECTION

Inspect the complete existing backend.

Determine:

### Runtime

Identify:

* Python version requirement
* FastAPI version
* Uvicorn version
* SQLAlchemy version
* Pydantic version
* Alembic version
* authentication/security libraries

Identify the dependency-management mechanism actually used:

```text
requirements.txt
requirements-dev.txt
pyproject.toml
poetry
pipenv
other
```

Do not introduce a new dependency-management system unless required for a clear stabilization reason.

---

## 7.1 Backend Dependencies

Inspect:

* declared dependencies
* imported packages
* development dependencies
* test dependencies
* unused/duplicate dependencies
* missing dependencies
* incompatible dependency versions

Do not perform major dependency upgrades during P0-001.

Do not replace libraries merely because another library is preferred.

---

# 8. BACKEND CONFIGURATION

Inspect the actual configuration implementation.

Search for:

```text
os.getenv
os.environ
BaseSettings
Settings
load_dotenv
dotenv
environment configuration
configuration classes
```

Determine:

* configuration files
* environment variable consumption
* default values
* hard-coded configuration
* development configuration
* production configuration assumptions

Create an inventory of environment variables actually consumed by the backend.

---

# 9. DATABASE CONFIGURATION

Inspect the existing database implementation.

Determine:

* database technology
* connection configuration
* SQLAlchemy setup
* session management
* model registration
* migration mechanism
* Alembic configuration
* database initialization

Determine whether runtime schema creation such as:

```python
Base.metadata.create_all()
```

is currently used.

If found, document it.

Do NOT redesign database initialization during P0-001.

Do NOT modify database models or relationships.

Database reconciliation will be handled in a separate task.

---

# 10. AUTHENTICATION CONFIGURATION

Inspect the current authentication implementation only for configuration/dependency understanding.

Identify:

* authentication library
* JWT implementation
* password hashing library
* token configuration
* authentication-related environment variables

Do NOT redesign authentication.

Do NOT change authentication behavior unless a minimal configuration correction is absolutely required for the existing application to start.

Authentication corrections will be handled separately.

---

# 11. FRONTEND INSPECTION

Inspect the complete existing frontend.

Determine:

### Runtime and framework

* Node.js requirement
* npm/yarn/pnpm
* Next.js version
* React version
* TypeScript version

Inspect actual files such as:

```text
package.json
package-lock.json
yarn.lock
pnpm-lock.yaml
next.config.*
tsconfig.json
```

only if they actually exist.

Do not assume filenames.

---

# 12. FRONTEND DEPENDENCIES

Inspect:

* runtime dependencies
* development dependencies
* package versions
* missing packages
* duplicate/conflicting packages
* scripts

Do NOT perform major framework upgrades.

Do NOT replace libraries without a specific stabilization requirement.

---

# 13. NODE_MODULES POLICY

The repository must NOT track:

```text
node_modules/
```

including:

```text
frontend/node_modules/
```

Do not delete the developer's local `node_modules` directory merely because it is ignored.

Verify Git tracking using appropriate Git commands.

The repository should track dependency manifests and lock files where applicable, such as:

```text
package.json
package-lock.json
```

Do not commit generated dependency directories.

---

# 14. FRONTEND ENVIRONMENT VARIABLES

Search the actual frontend source for:

```text
process.env
NEXT_PUBLIC_
.env
.env.local
environment configuration
API configuration
```

Create an inventory of variables actually consumed.

Pay particular attention to variables beginning with:

```text
NEXT_PUBLIC_
```

because these are exposed to browser-side code.

Do not place private secrets in `NEXT_PUBLIC_*` variables.

---

# 15. ENVIRONMENT TEMPLATE

Inspect the existing:

```text
.env.example
```

if present.

Compare it against the environment variables actually consumed by the backend and frontend.

Identify:

* missing variables
* obsolete variables
* incorrectly named variables
* variables with unsafe defaults
* variables that should not be public

Update `.env.example` only when justified by the actual codebase.

Do not add speculative variables merely because they might be useful in the future.

---

# 16. SECRET AND SECURITY AUDIT

Search the actual repository for obvious secrets and sensitive configuration.

Check for:

```text
API keys
JWT secrets
database passwords
cloud credentials
private keys
tokens
passwords
credential-bearing connection strings
.env files
.pem
.key
.p12
.pfx
```

Never expose actual secret values in the audit report.

If a real secret is discovered:

1. Identify the affected file.
2. Report that a secret exists.
3. Prevent it from being newly committed.
4. Replace hard-coded configuration with environment-variable references where appropriate.
5. Update `.env.example` if necessary.
6. State clearly that the credential should be rotated.

If the secret has already been pushed to GitHub, report that separately.

Do not rewrite Git history automatically.

---

# 17. GIT AUDIT

Inspect:

```text
.gitignore
Git status
tracked files
current branch
remote
recent commits
```

Verify that generated/development-only directories are not tracked.

At minimum check:

```text
.env
node_modules/
.venv/
venv/
__pycache__/
.next/
build/
dist/
coverage/
test-results/
playwright-report/
```

Do not assume every item exists.

Do not modify Git history.

Do not force-push.

Do not reset the repository.

Do not delete existing commits.

---

# 18. BUILD AND STARTUP VERIFICATION

After inspection and safe stabilization:

## Backend

Use the existing project dependency mechanism.

Verify, as far as possible:

* dependencies install
* application imports
* FastAPI application initializes
* development server starts
* configuration loads
* routes can be discovered

If startup requires an unavailable external service, do not invent credentials or infrastructure.

Document the blocker.

---

## Frontend

Use the actual package manager discovered from the repository.

If a valid `package-lock.json` exists, prefer:

```bash
npm ci
```

Otherwise use the appropriate existing package-manager command.

Verify:

```bash
npm run build
```

or the actual build command defined by the project.

Verify development startup where practical.

Do not upgrade major framework versions merely to make the build pass.

---

# 19. TEST BASELINE

Inspect existing testing infrastructure.

Identify whether the repository contains:

```text
unit tests
integration tests
API tests
frontend tests
E2E tests
linting
type checking
coverage
```

Run existing appropriate checks where practical.

Do NOT build a complete new testing framework in P0-001.

The objective is to establish the current baseline.

---

# 20. ALLOWED CHANGES

P0-001 MAY make minimal changes such as:

* `.gitignore` corrections
* `.env.example` corrections
* missing dependency declarations
* clearly broken imports caused by missing declared dependencies
* development configuration corrections
* startup configuration corrections
* safe documentation of actual configuration
* minimal scripts needed to reproduce the existing application
* removal of generated artifacts from Git tracking, while preserving local copies

Every modification must be documented.

---

# 21. PROHIBITED CHANGES

Do NOT:

* redesign the architecture
* redesign the database
* change database relationships
* change API contracts
* implement new APIs
* redesign authentication
* implement authorization
* implement AI Lecturer
* implement AI assessment
* implement performance analytics
* implement remedial learning
* redesign frontend pages
* redesign UI/UX
* introduce new paid services
* introduce new AI providers
* perform major framework upgrades
* replace working libraries without necessity
* delete functional modules
* perform broad refactoring
* modify business rules

These belong to separate tasks.

---

# 22. AUDIT REPORT

If the repository does not already contain the audit directory, create:

```text
docs/01_codebase_audit/
```

Then create:

```text
docs/01_codebase_audit/P0-001_BASELINE_AUDIT.md
```

This is the primary documentation artifact produced by P0-001.

The report must contain:

## A. Actual repository structure

Document what actually exists.

## B. Backend technology

Include:

* runtime
* framework versions
* dependency mechanism
* database technology
* migration technology
* authentication libraries

## C. Frontend technology

Include:

* Node.js requirement
* package manager
* Next.js
* React
* TypeScript

## D. Environment variables

Use:

| Variable | Consumer | Required | Default/Example | Secret? |
| -------- | -------- | -------- | --------------- | ------- |

Never include actual secret values.

## E. Dependency findings

| Component | Finding | Severity | Action |
| --------- | ------- | -------- | ------ |

## F. Configuration findings

| File | Finding | Severity | Action |
| ---- | ------- | -------- | ------ |

## G. Security findings

| Finding | Location | Severity | Action |
| ------- | -------- | -------- | ------ |

Never print credential values.

## H. Build/startup results

For each application:

```text
Command:
Result:
Status:
```

## I. Test baseline

Document existing tests and results.

## J. Changes made

List every modified/created file.

## K. Unresolved issues

Document anything that could not safely be resolved.

## L. Recommended next task

Recommend the next task based on actual findings.

Do not automatically assume P0-002 is required if the audit reveals a different prerequisite.

---

# 23. STOP CONDITIONS

Stop implementation and report the issue if:

1. An available authoritative specification conflicts with the code.
2. A database modification appears necessary.
3. An API contract appears incorrect.
4. Authentication behavior requires redesign.
5. A major dependency upgrade appears necessary.
6. A production secret is discovered.
7. A credential may already have been exposed.
8. A destructive change appears necessary.
9. Correct behavior cannot be determined from available project materials.
10. The task would require implementing a new business feature.

Do not silently make architectural decisions.

---

# 24. GIT SAFETY

Do NOT execute:

```text
git reset --hard
git push --force
git rebase main
```

Do not rewrite history.

Do not delete commits.

Do not push changes automatically unless explicitly instructed.

At the end, provide the exact Git commands recommended for the project owner.

---

# 25. REQUIRED FINAL REPORT

At completion, return:

## 1. Executive Summary

## 2. Actual Repository Structure

## 3. Backend Findings

## 4. Frontend Findings

## 5. Configuration Findings

## 6. Environment Variables

## 7. Dependency Findings

## 8. Security Findings

## 9. Build/Startup Results

## 10. Test Results

## 11. Changes Made

## 12. Files Created/Modified

## 13. Unresolved Issues

## 14. Acceptance Criteria

Use:

```text
PASS
FAIL
BLOCKED
NOT APPLICABLE
```

## 15. Recommended Next Task

Base this recommendation on the actual findings.

---

# 26. FINAL INSTRUCTION TO CURSOR

This is an **inspection and controlled stabilization task**.

Do not attempt to complete SYS.

Do not implement Phase 1.

Do not implement new business functionality.

Do not assume planned directories or documents exist.

Inspect the repository as it actually exists.

Use available project specifications if they are present.

If specifications are absent, explicitly report that fact.

Make only minimal changes required to establish a stable development baseline.

Document every change.

Do not silently make architectural decisions.

**Inspect → Analyze → Stabilize → Test → Document → Stop.**
