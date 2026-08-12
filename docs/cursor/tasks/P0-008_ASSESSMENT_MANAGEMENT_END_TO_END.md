# SYS — P0-008

# Assessment Management — End-to-End Functional Implementation

**Task ID:** P0-008
**Phase:** Phase 1 — Core Learning & Assessment
**Priority:** P0
**Type:** End-to-End Feature Implementation
**Status:** NOT_STARTED

---

# 1. OBJECTIVE

Implement the **Assessment Management module end-to-end** using the existing SYS repository architecture.

This task follows:

```text
P0-001 Repository / Dependency Stabilization
P0-002 Secrets / Configuration Hardening
P0-003 Authentication Field Consistency
P0-004 Authorization Role Enforcement
P0-005 Model / Schema / API Alignment
P0-006 Frontend API Configuration
P0-007 Course Management
```

P0-005 already addressed known Assessment model/schema/API mismatches.

Therefore, this task must **build functional Assessment Management on top of the existing implementation**, rather than repeating model/API alignment work.

The desired result is a usable Assessment Management workflow:

```text
Course
  ↓
Assessment List
  ↓
Create Assessment
  ↓
Assessment Details
  ↓
Edit Assessment
  ↓
Publish / Activate where supported
  ↓
Archive / Delete where supported
```

The feature must work across:

```text
Database
    ↓
Backend Model
    ↓
Schema / Validation
    ↓
Service / CRUD
    ↓
API
    ↓
Authentication
    ↓
Authorization
    ↓
Frontend API
    ↓
SYS Branding / Design System
    ↓
Frontend UI
    ↓
Validation / Error Handling
    ↓
Tests
```

This is a **functional development task**, not an audit task.

---

# 2. IMPLEMENTATION PRINCIPLE

Do not split this task into separate backend-only and frontend-only work.

Implement the complete functional slice.

The task is complete only when an authorized user can manage assessments from the SYS frontend and the changes persist through the backend/database.

Maximize functional implementation.

Minimize explanation, documentation, and token consumption.

---

# 3. INSPECT EXISTING IMPLEMENTATION FIRST

Before modifying anything:

1. Inspect the current Assessment model.
2. Inspect Assessment schemas.
3. Inspect Assessment CRUD/service.
4. Inspect Assessment routes.
5. Inspect existing Assessment migrations.
6. Inspect Course relationships.
7. Inspect authentication/current-user implementation.
8. Inspect authorization/role enforcement.
9. Inspect the Course Management implementation from P0-007.
10. Inspect existing frontend API configuration.
11. Inspect frontend authentication/user state.
12. Inspect existing frontend routing.
13. Inspect existing shared UI components.
14. Inspect the SYS Branding Asset family.
15. Inspect existing testing conventions.

Reuse existing architecture.

Do not create duplicate:

* models
* schemas
* services
* API clients
* authentication mechanisms
* authorization mechanisms
* UI frameworks
* branding systems

---

# 4. EXISTING ASSESSMENT CONTRACT

P0-005 specifically addressed known Assessment model/schema/API inconsistencies involving fields such as:

```text
description
duration
difficulty
status
created_at
```

Use the **actual current repository implementation as the source of truth**.

Do not blindly recreate or redesign these fields.

Inspect the current model, schema, routes, and migrations first.

If P0-005 introduced a migration or model change, reuse it.

Do not introduce duplicate fields.

---

# 5. ASSESSMENT RELATIONSHIP WITH COURSE

Assessments should be associated with the existing Course implementation.

Inspect the current relationship between:

```text
Course
Assessment
```

Use the existing relationship if present.

The Assessment workflow should allow an authorized user to:

1. Select an existing Course.
2. Create an Assessment associated with that Course.
3. View assessments associated with a Course.
4. View individual Assessment details.
5. Edit an Assessment.
6. Manage its existing lifecycle/status where supported.

Do not redesign the Course model.

Do not introduce duplicate Course references.

---

# 6. ASSESSMENT LIST

Implement the frontend Assessment list.

The list must:

* retrieve assessments from the backend
* display appropriate assessment information
* associate each assessment with its Course where supported
* display status where supported
* display duration where supported
* display difficulty where supported
* support navigation to Assessment details
* provide role-appropriate actions
* provide loading state
* provide empty state
* provide error handling

If the existing backend supports filtering by Course, use it.

Do not invent an unnecessary filtering API if the current architecture does not support it.

---

# 7. CREATE ASSESSMENT

Authorized users must be able to create an Assessment.

The creation workflow must:

* select an existing Course where required
* accept supported Assessment fields
* validate required fields
* validate appropriate field types
* validate duration if supported
* validate difficulty if supported
* validate status according to the existing schema/lifecycle
* submit to the existing backend API
* handle validation errors
* handle authentication errors
* handle authorization errors
* handle server errors
* indicate successful creation
* navigate to an appropriate Assessment view/list
* update the Assessment list after successful creation

Use the actual Assessment schema as the source of truth.

Do not create fields that the backend does not support.

---

# 8. ASSESSMENT DETAILS

Implement an Assessment details view.

The details view must display information supported by the existing model/schema, such as:

```text
Assessment title/name
Description
Course
Duration
Difficulty
Status
Created date
Updated date if supported
```

Only display fields actually available in the repository.

The details view must:

* load data from the backend
* handle loading
* handle not-found
* handle authorization failure
* handle server failure
* provide appropriate navigation
* provide role-appropriate actions

---

# 9. EDIT ASSESSMENT

Authorized users must be able to edit an Assessment.

The edit workflow must:

* load the existing Assessment
* populate supported fields
* allow modification of editable fields
* validate input
* submit changes
* handle API errors
* update the UI after successful modification

Do not allow modification of immutable fields if the existing model/design treats them as immutable.

Backend authorization remains authoritative.

---

# 10. ASSESSMENT STATUS / LIFECYCLE

Inspect the actual Assessment status implementation.

If the existing application supports states such as:

```text
draft
published
active
inactive
archived
```

or equivalent:

* use the existing values
* expose appropriate lifecycle controls to authorized users
* enforce valid transitions where already defined

Do not invent a new state machine.

If status exists only as a simple field and no transition logic exists, do not create an unnecessarily complex workflow.

Implement the simplest behavior consistent with the existing application design.

---

# 11. DELETE / ARCHIVE

Inspect the current Assessment lifecycle.

If the backend supports deletion:

* expose delete functionality to permitted roles
* require confirmation
* update the UI after successful deletion

If the application uses archive/inactive behavior:

* use the existing mechanism
* do not introduce a competing delete mechanism

Do not introduce soft-delete architecture merely for this task unless already required by the application.

---

# 12. ROLE-BASED ACCESS

Use the authorization mechanism established by P0-004.

Inspect the actual roles in the repository.

Do not invent new roles.

Determine the permitted Assessment operations from the existing application design.

The expected pattern may be:

```text
ADMIN
    full management

FACULTY
    assessment management where permitted

STUDENT
    assessment access/viewing where permitted
```

But the repository's actual authorization design is authoritative.

The backend must enforce permissions.

The frontend should reflect those permissions.

Frontend hiding of buttons is not a security mechanism.

---

# 13. BACKEND IMPLEMENTATION

Implement or complete the backend functionality required for Assessment Management.

Reuse:

```text
Assessment model
Assessment schemas
Assessment CRUD/service
Assessment routes
Course relationship
database session
authentication dependencies
authorization dependencies
existing error handling
```

Potential operations may include:

```text
GET
GET by ID
GET by Course
POST
PUT/PATCH
DELETE
status/lifecycle operation where already supported
```

Use the actual route conventions in the repository.

Do not create duplicate endpoints.

Do not arbitrarily rename existing endpoints.

Preserve existing API contracts where possible.

---

# 14. VALIDATION

Use the existing Pydantic/schema validation mechanism.

Validate:

* required fields
* supported data types
* Course association
* duration
* difficulty
* status
* invalid Assessment IDs
* non-existent Course IDs
* invalid request bodies

Only apply constraints that are supported by the existing application contract.

Do not invent arbitrary business rules.

---

# 15. DATABASE

Use the existing Assessment and Course database implementation.

Do not redesign either model.

Do not modify unrelated tables.

If a migration is genuinely required:

1. Confirm the field/change is required.
2. Create the smallest appropriate migration.
3. Preserve existing data.
4. Verify the migration.

Do not use runtime schema creation to bypass migrations.

---

# 16. SYS BRANDING ASSET FAMILY — MANDATORY

All Assessment frontend screens must follow the established **SYS Branding Asset family**.

Before implementing the UI, inspect:

* SYS branding documentation
* logo/brand assets
* theme configuration
* colors
* typography
* shared components
* existing Course Management UI from P0-007
* layout/navigation patterns

Reuse existing SYS components and assets.

Mandatory rules:

1. Do not invent a new logo.
2. Do not invent a new color palette.
3. Do not introduce arbitrary typography.
4. Do not create a parallel design system.
5. Reuse existing buttons.
6. Reuse existing cards.
7. Reuse existing forms.
8. Reuse existing dialogs.
9. Reuse existing navigation.
10. Reuse existing loading/error/empty states.
11. Maintain the visual relationship between Course and Assessment screens.

Assessment Management should look like a natural extension of Course Management.

---

# 17. FRONTEND DESIGN CONSISTENCY

Maintain consistency across:

```text
Assessment List
Assessment Details
Create Assessment
Edit Assessment
Delete/Archive confirmation
Loading state
Empty state
Validation state
Error state
```

Maintain consistency in:

```text
Typography
Colors
Spacing
Cards
Forms
Buttons
Icons
Navigation
Responsive behavior
```

Prefer existing components over creating new visually similar components.

If P0-007 created reusable Course Management components that are applicable, reuse them.

---

# 18. FRONTEND IMPLEMENTATION

Use the existing frontend architecture.

Reuse:

* existing layout
* navigation
* API client
* authentication state
* role state
* form components
* buttons
* cards
* dialogs
* theme
* responsive utilities
* SYS branding assets
* error handling

Do not introduce another UI framework.

Do not introduce another HTTP client.

Do not redesign the existing application shell.

---

# 19. ASSESSMENT ROUTING

Use the existing frontend routing conventions.

Implement appropriate routes/pages for:

```text
Assessments
Assessment Details
Create Assessment
Edit Assessment
```

If the existing application uses nested Course routes, follow that architecture.

Do not introduce a competing routing pattern.

---

# 20. COURSE → ASSESSMENT NAVIGATION

Where supported by the existing frontend architecture, provide a natural workflow:

```text
Courses
   ↓
Course Details
   ↓
Assessments
   ↓
Assessment Details
```

An authorized user should be able to create/manage assessments associated with the selected Course.

Do not duplicate Course information unnecessarily.

---

# 21. API INTEGRATION

Use the API configuration established in P0-006 and the API patterns established by P0-007.

Do not hardcode:

```text
localhost URLs
production URLs
API hostnames
```

Use the existing API client/configuration.

Authentication tokens/credentials must use the existing authentication mechanism.

Handle HTTP errors correctly.

---

# 22. ERROR HANDLING

Handle at least:

```text
400/422 → validation error
401     → authentication required/expired
403     → insufficient permissions
404     → Course/Assessment not found
409     → conflict if applicable
500     → server error
```

Use existing SYS error-handling components.

Do not expose backend stack traces.

---

# 23. ACCESSIBILITY

Follow existing SYS accessibility conventions.

Ensure:

* form controls have labels
* buttons have meaningful names
* keyboard navigation works
* validation errors are understandable
* dialogs are accessible
* semantic HTML is used appropriately

Do not introduce a separate accessibility framework.

---

# 24. RESPONSIVE DESIGN

Assessment Management must follow existing SYS responsive behavior.

Verify reasonable presentation on:

```text
Desktop
Tablet
Mobile
```

Reuse existing responsive components/utilities.

Do not redesign responsive architecture.

---

# 25. TESTS — BACKEND

Add or update relevant tests.

Test:

```text
Assessment list
Assessment details
Assessment creation
Assessment update
Assessment deletion/archive where supported
Course association
Validation
Not-found behavior
Authentication
Authorization
```

At minimum verify:

* unauthenticated protected operations are rejected
* permitted roles can perform permitted operations
* insufficient roles are rejected
* valid Assessment creation works
* Assessment retrieval works
* Assessment update works
* invalid data is rejected
* invalid Course association is handled
* missing Assessment is handled

Reuse the existing testing framework.

---

# 26. TESTS — FRONTEND

If frontend tests already exist, add appropriate tests for:

* Assessment list rendering
* loading state
* empty state
* error state
* create form
* edit form
* role-based actions
* API interaction

If no frontend test framework exists, do not introduce a large framework solely for this task.

At minimum verify:

```text
frontend build/type-check
frontend startup
```

and perform practical workflow verification.

---

# 27. END-TO-END VERIFICATION

Verify the following complete workflow:

```text
Login
   ↓
Open Courses
   ↓
Open a Course
   ↓
Open Assessments
   ↓
Create Assessment
   ↓
Assessment persists in database
   ↓
Assessment appears in list
   ↓
Open Assessment Details
   ↓
Edit Assessment
   ↓
Updated data persists
   ↓
List reflects update
   ↓
Publish/activate if supported
   ↓
Delete/archive if supported
   ↓
List reflects final state
```

Do not claim end-to-end verification unless actually performed.

---

# 28. NO UNRELATED REFACTORING

This is an end-to-end feature task, so modifying multiple backend/frontend files is expected.

However, do not modify unrelated:

* authentication architecture
* authorization architecture
* Course behavior
* unrelated APIs
* unrelated frontend screens
* AI modules
* deployment infrastructure
* dependencies
* global styling

unless directly required for Assessment Management.

If a P0-007 Course Management component needs a small reusable improvement to support Assessment Management, make the smallest appropriate change.

---

# 29. DEPENDENCY POLICY

Do not add dependencies unless genuinely necessary.

Before adding a dependency:

1. Check existing dependencies.
2. Reuse existing utilities.
3. Add only if no reasonable existing solution exists.
4. Keep dependency changes minimal.

Do not perform major framework upgrades.

---

# 30. TOKEN EFFICIENCY

The primary deliverable is **working functionality**.

Do not spend significant token budget on:

* lengthy explanations
* architecture essays
* repeated task summaries
* extensive documentation
* describing obvious code changes

Implement first.

Test second.

Report briefly.

---

# 31. GIT SAFETY

Do NOT execute:

```text
git reset --hard
git rebase
git filter-repo
git filter-branch
git push --force
```

Do not rewrite Git history.

Do not delete commits.

Do not commit automatically unless explicitly instructed.

Before completion:

```bash
git status
```

must be checked.

Do not modify unrelated uncommitted work.

---

# 32. ACCEPTANCE CRITERIA

## Backend

* [ ] Existing Assessment model is reused.
* [ ] Existing Course relationship is respected.
* [ ] Assessment CRUD/read functionality works.
* [ ] Assessment validation works.
* [ ] Authentication is integrated.
* [ ] Authorization is enforced server-side.
* [ ] Appropriate error responses are returned.
* [ ] Existing API contracts are preserved where possible.

## Database

* [ ] Assessment data persists correctly.
* [ ] Course association persists correctly.
* [ ] Existing migrations are respected.
* [ ] Any required migration is minimal and verified.
* [ ] No unrelated database changes are introduced.

## Frontend

* [ ] Assessment list is implemented.
* [ ] Assessment details are implemented.
* [ ] Assessment creation is implemented.
* [ ] Assessment editing is implemented.
* [ ] Existing status/lifecycle mechanism is integrated where supported.
* [ ] Existing delete/archive mechanism is integrated where supported.
* [ ] Course → Assessment navigation works.
* [ ] Authentication is integrated.
* [ ] Role-based UI behavior is implemented.
* [ ] Loading/empty/error states are handled.
* [ ] Responsive behavior follows SYS conventions.

## SYS Branding

* [ ] SYS Branding Asset family has been inspected.
* [ ] Existing SYS assets are reused.
* [ ] Existing typography is preserved.
* [ ] Existing colors/theme are preserved.
* [ ] Existing shared components are reused.
* [ ] Assessment screens visually match Course Management.
* [ ] No parallel design system has been introduced.

## Integration

* [ ] Frontend communicates successfully with backend.
* [ ] Assessment creation persists.
* [ ] Assessment updates persist.
* [ ] Course association works.
* [ ] Unauthorized operations are rejected.
* [ ] Existing authentication/authorization behavior remains functional.

## Verification

* [ ] Backend tests pass.
* [ ] Frontend verification passes.
* [ ] Application startup succeeds.
* [ ] End-to-end Assessment workflow has been verified.
* [ ] No real secrets were introduced.
* [ ] No unrelated files were unnecessarily modified.

---

# 33. BLOCKER POLICY

Resolve ordinary implementation problems within this task.

Do not stop because a missing CRUD operation, frontend component, validation rule, or integration needs to be implemented.

Stop and report only if the issue requires a major architectural decision, such as:

* authentication redesign
* authorization redesign
* database architecture redesign
* frontend framework replacement
* backend framework replacement
* fundamental API contract redesign
* major external service introduction
* destructive database migration

---

# 34. FINAL RESPONSE TO PROJECT OWNER

Do NOT provide a long report.

Return only:

```text
Files changed:
<list>

Functionality completed:
<short summary>

Backend tests:
PASS / FAIL

Frontend verification:
PASS / FAIL

SYS branding verification:
PASS / FAIL

End-to-end verification:
PASS / FAIL

Build/startup:
PASS / FAIL

Remaining blocker:
<None or concise description>
```

Do not repeat the task specification.

Do not explain every code change.

Do not generate extensive documentation.

---

# 35. FINAL INSTRUCTION

This is a **functional product-development task**.

Do not treat it as an audit, stabilization, or configuration task.

Use the existing foundation from P0-001 through P0-007.

Implement **Assessment Management end-to-end**.

The desired result is:

```text
Course
   ↓
Assessment Management
   ↓
Create / View / Edit
   ↓
Persist
   ↓
Role Enforcement
   ↓
SYS-branded Frontend
```

The implementation must be usable from the frontend and persist correctly through the backend/database.

Work in this order:

```text
Inspect existing implementation
        ↓
Inspect Course Management integration
        ↓
Inspect SYS Branding Asset family
        ↓
Reuse existing backend/frontend components
        ↓
Implement missing backend functionality
        ↓
Implement frontend functionality
        ↓
Integrate Course → Assessment workflow
        ↓
Apply SYS branding/design system
        ↓
Integrate authentication/authorization
        ↓
Implement validation/error handling
        ↓
Test
        ↓
Build/startup verification
        ↓
End-to-end verification
        ↓
Concise report
```

**Maximize actual functionality delivered per Cursor task. Minimize explanation, documentation, and unnecessary refactoring.**

Do not start another major feature until Assessment Management is actually functional.
