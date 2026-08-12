# SYS — P0-007

# Course Management — End-to-End Functional Implementation

**Task ID:** P0-007
**Phase:** Phase 0 → Functional Development Transition
**Priority:** P0
**Type:** End-to-End Feature Implementation
**Status:** NOT_STARTED

---

# 1. OBJECTIVE

Implement the **Course Management module end-to-end** using the existing SYS repository architecture.

This is the first major functional development task after the repository stabilization, security hardening, authentication, authorization, model/API alignment, and frontend API configuration work completed in P0-001 through P0-006.

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
Authentication / Authorization
    ↓
Frontend API integration
    ↓
SYS Branding / Design System
    ↓
Frontend UI
    ↓
Validation / Error handling
    ↓
Tests
```

The objective is to deliver a **working Course Management feature**, not merely create backend infrastructure.

Do not stop after implementing APIs.

Do not stop after implementing frontend components.

The feature is complete only when the frontend can use the backend successfully.

---

# 2. INSPECT EXISTING IMPLEMENTATION FIRST

Before modifying anything:

1. Inspect the current repository.
2. Inspect the existing Course model.
3. Inspect Course schemas.
4. Inspect Course CRUD/service implementation.
5. Inspect Course routes.
6. Inspect existing migrations.
7. Inspect authentication/current-user implementation.
8. Inspect role enforcement from P0-004.
9. Inspect the existing frontend architecture.
10. Inspect the frontend API configuration established by P0-006.
11. Inspect existing frontend shared components.
12. Inspect existing authentication/user state handling.
13. Inspect existing frontend routing.
14. Inspect existing SYS Branding Asset family and design-system implementation.
15. Inspect existing tests.

Reuse the existing architecture wherever possible.

Do NOT create duplicate models, services, API clients, authentication mechanisms, UI systems, or branding systems.

---

# 3. EXISTING COURSE CONTRACT

P0-005 addressed confirmed Course model/schema/API alignment, including existing Course fields such as:

```text
duration
category
```

Use the **actual current Course model, schemas, routes, and API contract in the repository as the source of truth**.

Do not invent a new Course data model.

Do not redesign the existing Course schema merely to make this task easier.

If the current repository contains additional Course fields, use them where appropriate.

If a required field is genuinely missing, determine whether it is required by the existing application design before changing the database.

---

# 4. FUNCTIONAL SCOPE

Implement the following Course Management workflow:

```text
Course List
    ↓
Course Details
    ↓
Create Course
    ↓
Edit Course
    ↓
Delete / Deactivate where supported
```

The complete workflow must be integrated with:

```text
Authentication
Authorization
Backend API
Database
Frontend
SYS Branding
```

---

# 5. COURSE LIST

Provide a frontend page that displays available courses.

The page must:

* retrieve courses from the existing backend API
* display appropriate course information based on the existing schema
* use the existing frontend API configuration
* provide loading state
* provide empty state
* provide API error handling
* provide appropriate actions according to the authenticated user's role
* allow the user to open/view a course

Do not hardcode an API URL.

Do not create a duplicate API client if one already exists.

---

# 6. COURSE CREATION

Authorized users must be able to create a course.

Use the existing authorization design.

The creation workflow must:

* display the appropriate Course fields
* validate required fields
* validate supported field types/constraints
* display validation errors
* submit through the existing API
* handle authentication errors
* handle authorization errors
* handle server errors
* indicate successful creation
* return the user to an appropriate Course view/list
* refresh or update the Course list after successful creation

The backend must remain the authoritative security boundary.

Do not rely on frontend-only authorization.

---

# 7. COURSE DETAILS

Implement a Course details view using the existing frontend routing architecture.

The details view must:

* retrieve the selected course from the backend
* display the course information supported by the existing model/schema
* provide loading state
* handle not-found responses
* handle API errors
* provide navigation back to the Course list
* provide role-appropriate actions

Do not duplicate course data unnecessarily.

---

# 8. COURSE UPDATE

Authorized users must be able to edit an existing Course.

The implementation must:

* retrieve the existing Course
* populate the edit form
* allow modification of supported fields
* validate input
* submit changes to the backend
* handle validation errors
* handle authorization errors
* handle API/server errors
* update the displayed Course after successful modification

Backend authorization must be enforced.

Do not allow unauthorized users to update Courses merely because the frontend hides the edit button.

---

# 9. COURSE DELETE / DEACTIVATION

Inspect the existing Course model/API to determine whether the current application supports:

```text
delete
```

or:

```text
active/inactive
status
```

or another existing lifecycle mechanism.

Use the existing design.

If deletion is already supported:

* implement the existing delete operation
* require appropriate confirmation
* handle errors
* update the Course list

If an active/inactive mechanism already exists:

* use that mechanism
* do not invent another lifecycle architecture

Do NOT introduce a new lifecycle field merely for this task unless clearly required by the existing application contract.

---

# 10. ROLE-BASED ACCESS

Use the authorization mechanism established by P0-004.

Inspect the actual role values in the repository.

Relevant roles may include:

```text
ADMIN
FACULTY
STUDENT
```

Do not assume additional roles exist.

Determine permitted Course operations from the existing application design.

The frontend must:

* show appropriate actions according to the user's role
* prevent unnecessary navigation to unauthorized operations
* handle 401/403 responses correctly

The backend must:

* enforce the actual authorization rules
* reject unauthorized operations regardless of frontend behavior

Do not duplicate or redesign the existing authorization framework.

---

# 11. BACKEND IMPLEMENTATION

Implement or complete the backend functionality required for the Course Management workflow.

Inspect and reuse:

```text
Course model
Course schemas
Course CRUD/service
Course routes
database session
authentication dependencies
authorization dependencies
existing error handling
```

Implement only missing functionality.

Potential operations may include:

```text
GET       /courses
GET       /courses/{id}
POST      /courses
PUT/PATCH /courses/{id}
DELETE    /courses/{id}
```

Use the actual route conventions already present.

Do NOT create duplicate routes.

Do NOT arbitrarily rename existing API endpoints.

Preserve existing API contracts wherever possible.

---

# 12. BACKEND VALIDATION

Course creation and update must validate input appropriately.

Use the project's existing Pydantic/schema validation approach.

Validation should cover:

* required fields
* supported data types
* existing schema constraints
* invalid identifiers
* missing/non-existent Course records
* invalid Course data

Do not introduce another validation framework.

---

# 13. DATABASE

Use the existing Course model and database configuration.

Do NOT redesign the database.

Do NOT change unrelated models.

Do NOT change unrelated relationships.

If a database migration is genuinely required because the current Course implementation is incomplete:

1. Confirm the change is required by the existing application contract.
2. Create the smallest appropriate Alembic migration.
3. Do not modify unrelated tables.
4. Verify the migration.

Do not use runtime schema creation as a substitute for migrations.

---

# 14. SYS BRANDING ASSET FAMILY — MANDATORY

The Course Management frontend must follow the established **SYS Branding Asset family** and must visually belong to the existing SYS product.

Before creating or modifying frontend UI, inspect the repository for the existing SYS branding assets, design-system documentation, shared components, theme configuration, and visual conventions.

Search for and reuse existing SYS:

* logo / brand mark
* favicon / application icon where applicable
* brand colors
* typography
* font configuration
* buttons
* cards
* form controls
* input fields
* navigation
* header/sidebar
* page layouts
* badges
* dialogs/modals
* icons
* illustrations
* empty states
* loading states
* error states
* tables/lists
* dashboard components
* spacing/layout conventions
* border/radius/shadow conventions
* responsive behavior

### Mandatory rules

1. **Reuse existing SYS branding assets whenever they exist.**
2. **Reuse existing shared UI components whenever they provide the required functionality.**
3. Do not create a separate visual language for Course Management.
4. Do not invent a new logo.
5. Do not invent a new brand color palette.
6. Do not introduce arbitrary fonts.
7. Do not create visually inconsistent buttons, cards, forms, dialogs, or navigation.
8. Do not replace an existing branded component with a newly designed alternative without a functional reason.
9. Extend the existing design system rather than creating a parallel design system.
10. New Course screens must look like native parts of the SYS application.

If the repository contains an authoritative SYS Branding Asset specification, follow it as the source of truth.

If branding assets are present in the repository but their usage is unclear, inspect how existing screens use them and follow the established pattern.

If a required branding asset is genuinely missing:

* do not invent an unrelated replacement
* use the closest existing SYS component/pattern where practical
* report the missing asset briefly in the final response

Do not block ordinary functional implementation merely because a non-essential branding asset is unavailable.

---

# 15. FRONTEND DESIGN CONSISTENCY

The following screens must maintain consistent SYS visual identity:

```text
Courses
Course Details
Create Course
Edit Course
Delete/Deactivate confirmation
Validation messages
Loading states
Empty states
Error states
```

The screens must feel like a single coherent product.

Maintain consistency in:

```text
Typography
Colors
Spacing
Layout
Buttons
Cards
Forms
Icons
Navigation
Responsive behavior
```

Do not create a page that visually looks unrelated to the existing SYS frontend.

Before creating a new component, check whether an equivalent shared component already exists.

---

# 16. FRONTEND IMPLEMENTATION

Inspect the existing frontend architecture before creating components.

Reuse existing:

* layout
* navigation
* shared components
* forms
* buttons
* cards
* dialogs
* API client
* authentication state
* user/role state
* error handling
* styling system
* theme
* SYS branding assets

Do not introduce another UI framework.

Do not introduce another HTTP client if one already exists.

Do not redesign the entire frontend.

Create only the pages/components required for Course Management.

---

# 17. FRONTEND PAGES / COMPONENTS

Implement the appropriate existing frontend routing structure for:

```text
Courses
Course Details
Create Course
Edit Course
```

These may be separate pages or components depending on the existing Next.js architecture.

Do not force a new routing architecture.

The Course list should provide appropriate actions according to the authenticated user's role.

---

# 18. USER EXPERIENCE

Provide clear and consistent SYS-branded states for:

```text
Loading
Empty
Success
Validation error
Authentication error
Authorization error
Not found
Server error
```

Use existing SYS components for these states whenever available.

Prioritize functional usability and consistency over unnecessary animation or visual effects.

---

# 19. API INTEGRATION

Use the frontend API configuration established by P0-006.

The implementation must:

* obtain the API base URL from the existing environment/configuration mechanism
* use the existing API client where present
* send authentication credentials/tokens according to the existing authentication implementation
* handle HTTP errors correctly
* avoid hardcoded production URLs

Do not reintroduce obsolete environment-variable conventions.

Do not reintroduce:

```text
REACT_APP_API_URL
```

where it is incompatible with the actual frontend build system.

---

# 20. AUTHENTICATION

Use the existing authentication implementation.

Do not redesign:

* JWT generation
* password hashing
* login
* registration
* token architecture

Only integrate Course Management with the existing authentication mechanism.

Authenticated API requests must use the established mechanism.

---

# 21. AUTHORIZATION

Use the existing authorization dependencies established by P0-004.

Verify:

```text
unauthenticated
    → rejected where authentication is required

authenticated + permitted role
    → allowed

authenticated + insufficient role
    → rejected
```

Do not create a parallel authorization mechanism.

---

# 22. TESTS

Add or update tests for the Course Management workflow.

## Backend

Test the relevant operations:

```text
course list
course details
course creation
course update
course deletion/deactivation if supported
validation failures
not-found behavior
authentication failures
authorization failures
```

At minimum verify:

* unauthenticated protected operations are rejected
* permitted roles can perform permitted operations
* insufficient roles are rejected
* valid Course creation works
* Course retrieval works
* Course update works
* invalid data is rejected
* missing Course is handled correctly

Reuse the existing testing framework.

Do not create an entirely new test framework.

---

# 23. FRONTEND VERIFICATION

Verify:

```text
frontend starts successfully
course list loads
course details load
course creation works
course update works
delete/deactivation works if supported
API errors are handled
role-based controls behave correctly
SYS branding is preserved
```

Use the existing frontend test/build/type-check mechanisms.

If automated frontend tests already exist, extend them appropriately.

If no frontend testing infrastructure exists, perform practical build/type-check validation without introducing a large testing framework solely for this task.

---

# 24. END-TO-END VERIFICATION

The most important acceptance workflow is:

```text
Login
   ↓
Open Courses
   ↓
Retrieve courses from backend
   ↓
Create a Course as an authorized user
   ↓
Course persists in database
   ↓
Course appears in list
   ↓
Open Course Details
   ↓
Edit Course
   ↓
Updated information persists
   ↓
Course list reflects update
   ↓
Delete/deactivate if supported
   ↓
Course list reflects final state
```

Verify this workflow using the actual application where practical.

Do not claim end-to-end success unless it was actually verified.

---

# 25. ERROR HANDLING

Handle common backend responses appropriately:

```text
400/422 → validation error
401     → authentication required/expired
403     → insufficient permissions
404     → Course not found
409     → conflict if applicable
500     → server error
```

Use existing SYS/frontend error-handling conventions.

Do not expose internal stack traces to users.

---

# 26. RESPONSIVE FRONTEND

Course Management screens must follow the existing SYS responsive design conventions.

Verify reasonable behavior for:

```text
Desktop
Tablet
Mobile
```

Do not redesign the responsive architecture.

Reuse existing responsive layout utilities/components.

---

# 27. ACCESSIBILITY

Use the existing frontend accessibility conventions.

At minimum:

* form controls must have appropriate labels
* buttons must have meaningful accessible names
* interactive elements must be keyboard accessible
* validation errors should be understandable
* dialogs/confirmation controls should be accessible
* semantic HTML should be used where appropriate

Do not introduce a separate accessibility framework.

---

# 28. NO UNRELATED REFACTORING

This task is intentionally larger than P0-001 through P0-006.

It is acceptable to modify multiple backend and frontend files because this is an end-to-end feature.

However:

**Do not refactor unrelated modules.**

Do not change:

* authentication architecture
* authorization architecture
* unrelated APIs
* unrelated UI pages
* AI modules
* deployment infrastructure
* unrelated dependencies
* project-wide styling

unless a confirmed blocker directly affects Course Management.

---

# 29. DEPENDENCY POLICY

Do not add new dependencies unless genuinely required.

Before adding a dependency:

1. Check whether an existing dependency already provides the required functionality.
2. Prefer existing project utilities.
3. Add a dependency only when there is no reasonable existing solution.
4. Keep the change minimal.

Do not upgrade major framework/library versions as part of this task.

---

# 30. DOCUMENTATION / TOKEN EFFICIENCY

The primary objective is **functional implementation**, not documentation.

Do NOT spend significant token budget generating:

* long architecture reports
* repeated task summaries
* extensive explanations of every file
* documentation that does not directly support the feature

Do not create a long implementation report.

Update task status/documentation only if the repository's existing workflow requires it.

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

Do not delete existing commits.

Do not commit automatically unless explicitly instructed.

Before completion run:

```bash
git status
```

Do not modify unrelated uncommitted user work.

---

# 32. ACCEPTANCE CRITERIA

## Backend

* [ ] Existing Course model is reused.
* [ ] Required Course API operations are implemented or completed.
* [ ] Course validation works.
* [ ] Authentication integration works.
* [ ] Authorization is enforced server-side.
* [ ] Appropriate error responses are returned.
* [ ] Existing API contracts are preserved where possible.
* [ ] Existing authentication/authorization behavior is not broken.

## Database

* [ ] Course data persists correctly.
* [ ] Existing migrations are respected.
* [ ] Any required migration is minimal and verified.
* [ ] No unrelated database changes are introduced.

## Frontend

* [ ] Course list is implemented.
* [ ] Course details are implemented.
* [ ] Course creation is implemented.
* [ ] Course editing is implemented.
* [ ] Existing delete/deactivation mechanism is integrated where supported.
* [ ] API configuration uses the existing environment mechanism.
* [ ] Authentication is integrated.
* [ ] Role-based UI behavior is implemented.
* [ ] Loading/empty/error states are handled.
* [ ] Responsive behavior follows existing SYS conventions.

## SYS Branding

* [ ] Existing SYS Branding Asset family has been inspected.
* [ ] Existing SYS logo/brand assets are reused where applicable.
* [ ] Existing SYS typography/theme is preserved.
* [ ] Existing SYS colors are preserved.
* [ ] Existing shared UI components are reused where applicable.
* [ ] Course screens visually match the existing SYS frontend.
* [ ] No parallel branding/design system has been introduced.
* [ ] No arbitrary new logo, color palette, or typography has been introduced.

## Integration

* [ ] Frontend successfully communicates with backend.
* [ ] Created Courses persist in the database.
* [ ] Updated Courses persist correctly.
* [ ] Course list reflects backend state.
* [ ] Unauthorized operations are rejected by backend.
* [ ] Existing authentication and authorization tests remain functional.

## Verification

* [ ] Backend tests pass.
* [ ] Relevant frontend checks pass.
* [ ] Application startup succeeds.
* [ ] End-to-end Course workflow has been verified.
* [ ] No real secrets were introduced.
* [ ] No unrelated files were unnecessarily modified.

---

# 33. BLOCKER POLICY

Do not stop merely because a normal implementation issue is discovered.

Resolve ordinary implementation issues within the scope of this task.

Stop and report only if the blocker requires a major architectural decision, such as:

* redesigning authentication
* redesigning authorization
* redesigning database architecture
* replacing the frontend framework
* replacing the backend framework
* changing a fundamental API contract
* introducing a major external service
* destructive database changes

For ordinary missing CRUD/schema/UI functionality, implement it.

---

# 34. FINAL RESPONSE TO PROJECT OWNER

Do NOT generate a lengthy report.

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

Do not provide a long architectural essay.

Do not create additional documentation unless required by the implementation.

---

# 35. FINAL INSTRUCTION

This task marks the transition from **repository stabilization** to **actual SYS product development**.

Do not treat this as another audit or configuration task.

Use the existing architecture established by P0-001 through P0-006.

Implement the Course Management feature **end-to-end**.

The desired result is a **working Course Management workflow that can be used from the frontend, persists data through the backend/database, respects authentication and authorization, and visually belongs to the SYS product through consistent use of the SYS Branding Asset family.**

Work in this order:

```text
Inspect existing implementation
        ↓
Inspect SYS Branding Asset family / design system
        ↓
Identify reusable backend/frontend components
        ↓
Implement missing backend functionality
        ↓
Implement frontend functionality
        ↓
Apply existing SYS branding/design system
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

**Maximize functional implementation. Minimize explanation, documentation, and unnecessary refactoring.**

Do not move to another feature until the Course Management workflow is actually functional.
