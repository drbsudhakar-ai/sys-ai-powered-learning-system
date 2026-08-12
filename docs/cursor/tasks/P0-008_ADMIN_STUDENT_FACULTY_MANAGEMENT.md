# SYS — P0-008

# Admin Student & Faculty Management + Academic Responsibility Assignment

**Task ID:** P0-008
**Phase:** Phase 1 — Core Academic Management
**Priority:** P0
**Type:** End-to-End Functional Implementation
**Status:** NOT_STARTED

---

# 1. OBJECTIVE

Implement the **Admin Student & Faculty Management + Academic Responsibility Assignment** module end-to-end.

This is a major functional SYS feature.

The objective is to provide Admin users with a complete interface for managing:

1. Students
2. Faculty
3. Faculty academic responsibilities
4. Course Coordinator assignments
5. Subject Expert assignments

The implementation must work across:

Database
    ↓
Backend Models
    ↓
Schemas / Validation
    ↓
Services / CRUD
    ↓
API
    ↓
Authentication
    ↓
Authorization
    ↓
Frontend API integration
    ↓
SYS Branding / Design System
    ↓
Frontend UI
    ↓
Tests
    ↓
End-to-end verification

This is NOT an audit task.

This is NOT merely a user CRUD task.

Implement the complete functional workflow.

---

# 2. IMPORTANT ARCHITECTURAL DISTINCTION

SYS has two different concepts that MUST NOT be incorrectly merged.

## System Roles

The existing application system roles include:

ADMIN
FACULTY
STUDENT

Use the actual role values already present in the repository as the source of truth.

## Academic Responsibilities

Academic responsibilities are separate from system roles.

The intended academic responsibilities are:

COURSE_COORDINATOR
SUBJECT_EXPERT

A Faculty user may have:

- no academic responsibility
- Course Coordinator responsibility
- Subject Expert responsibility
- both Course Coordinator and Subject Expert responsibilities

Do NOT create:

ROLE_COURSE_COORDINATOR
ROLE_SUBJECT_EXPERT

unless the existing repository already defines them as system roles.

Prefer representing these as academic responsibility/assignment relationships.

---

# 3. EXPECTED HIGH-LEVEL MODEL

The intended conceptual structure is:

Admin
    ↓
Faculty
    ├── System Role: FACULTY
    ├── Course Coordinator assignments
    └── Subject Expert assignments

Student
    └── System Role: STUDENT

Course
    └── Course Coordinator → Faculty

Subject / academic subject
    └── Subject Expert → Faculty

The exact database representation MUST follow the existing repository architecture.

Do not blindly create this structure if equivalent entities/relationships already exist.

Inspect first.

---

# 4. INSPECT EXISTING IMPLEMENTATION FIRST

Before modifying files, inspect:

1. Existing User model.
2. Existing Student representation.
3. Existing Faculty representation.
4. Existing role implementation.
5. Existing authentication.
6. Existing authorization from P0-004.
7. Existing Course model.
8. Existing Course CRUD/API from P0-007.
9. Existing Subject-related models, if any.
10. Existing academic relationships.
11. Existing frontend authentication state.
12. Existing frontend user/role state.
13. Existing frontend API client.
14. Existing SYS Branding Asset family.
15. Existing shared UI components.
16. Existing tests.
17. Existing migrations.

IMPORTANT:

Reuse existing functionality.

Do not create duplicate User, Student, Faculty, Course, or Subject entities if they already exist.

---

# 5. EXISTING COURSE MANAGEMENT INTEGRATION

P0-007 implemented Course Management.

Use the actual implementation from P0-007.

Do NOT recreate Course Management.

P0-008 must extend the existing Course implementation where necessary to support:

- Course Coordinator assignment
- Subject Expert assignment where applicable

Preserve the existing Course CRUD behavior.

Do not break:

- Course list
- Course details
- Course creation
- Course update
- Course deletion

---

# 6. ADMIN ACCESS

This entire management module is primarily an Admin capability.

The backend MUST enforce Admin authorization.

Expected baseline behavior:

Unauthenticated
    → 401

Student
    → 403

Faculty
    → 403 for Admin-only management operations

Admin
    → allowed

Do not rely on frontend hiding.

The backend must remain the authoritative security boundary.

Use the existing authorization mechanism from P0-004.

Do not create a second authorization system.

---

# 7. STUDENT MANAGEMENT

Implement complete Admin Student Management.

Admin must be able to:

- list students
- view student details
- create student
- edit student
- activate/deactivate student where supported
- delete student only if the existing application architecture permits deletion

Do not introduce destructive deletion if the existing user/account architecture requires deactivation instead.

Inspect the current design first.

---

# 8. STUDENT LIST

Create a SYS-branded Student Management page.

The list should display appropriate existing student information.

Possible information includes:

- name
- username/email
- student identifier where available
- status
- academic information where already supported

Use only fields that actually exist in the repository.

Do not invent unnecessary student profile fields.

The list must provide:

- loading state
- empty state
- error state
- appropriate actions
- navigation to student details

---

# 9. CREATE STUDENT

Admin must be able to create a Student.

The workflow must:

1. Open the Student creation form.
2. Accept the fields supported by the existing User/Student model.
3. Validate required fields.
4. Validate supported formats.
5. Assign the STUDENT system role using the existing role mechanism.
6. Persist the account.
7. Handle duplicate/conflict errors.
8. Handle validation errors.
9. Handle server errors.
10. Show successful creation.
11. Update the Student list.

Do NOT implement password handling independently from the existing authentication architecture.

Reuse the existing password hashing/account creation mechanism.

Never store plaintext passwords.

---

# 10. STUDENT DETAILS

Implement a Student details view.

Display only information available in the existing data model.

The details view must support:

- loading
- not found
- authorization error
- server error
- navigation
- edit/deactivate actions where permitted

Do not expose sensitive authentication data.

Never display:

- password hashes
- authentication secrets
- tokens
- internal security information

---

# 11. EDIT STUDENT

Admin must be able to edit supported Student information.

The implementation must:

- load existing data
- populate the form
- validate changes
- persist updates
- handle errors
- refresh displayed information

Do not allow arbitrary modification of protected authentication fields.

Use the existing User/Student architecture.

---

# 12. STUDENT ACTIVATION / DEACTIVATION

Inspect the current account/status implementation.

If the repository supports active/inactive status:

Implement Admin controls to:

- activate
- deactivate

If no such mechanism exists:

Do NOT invent an unnecessarily complex account lifecycle.

Determine the smallest architecture-compatible solution.

Do not introduce duplicate status fields.

---

# 13. FACULTY MANAGEMENT

Implement complete Admin Faculty Management.

Admin must be able to:

- list faculty
- view faculty details
- create faculty
- edit faculty
- activate/deactivate where supported
- manage academic responsibilities

Faculty accounts must use the existing FACULTY system role.

Do NOT create a separate authentication mechanism for faculty.

---

# 14. FACULTY LIST

Create a SYS-branded Faculty Management page.

Display appropriate existing faculty information.

Where available, display:

- name
- username/email
- status
- academic responsibilities
- assigned Courses
- assigned Subjects

Only display relationships that actually exist after implementation.

Provide:

- loading state
- empty state
- error state
- details navigation
- role-appropriate actions

---

# 15. CREATE FACULTY

Admin must be able to create a Faculty account.

The workflow must:

1. Create the account using existing authentication architecture.
2. Assign FACULTY as the system role.
3. Validate required fields.
4. Handle duplicate account errors.
5. Handle validation errors.
6. Persist the faculty account.
7. Update the Faculty list.

Do not create separate faculty authentication.

---

# 16. FACULTY DETAILS

Implement Faculty details.

Display appropriate existing information.

Where supported, show:

System role:
    FACULTY

Academic responsibilities:
    Course Coordinator
    Subject Expert

Assignments:
    Courses
    Subjects

Do not display sensitive authentication information.

---

# 17. EDIT FACULTY

Admin must be able to edit supported faculty information.

The workflow must:

- load existing faculty
- populate form
- validate input
- save changes
- update UI
- handle errors

Do not allow changing the fundamental account role through arbitrary form fields.

If role changes are supported by the existing architecture, handle them through the existing authorization/account mechanism.

---

# 18. ACADEMIC RESPONSIBILITY MANAGEMENT

This is a core requirement of P0-008.

Admin must be able to manage academic responsibilities for Faculty.

The responsibilities are:

COURSE_COORDINATOR
SUBJECT_EXPERT

These are academic responsibilities, NOT system roles.

---

# 19. COURSE COORDINATOR ASSIGNMENT

Admin must be able to assign a Faculty member as Course Coordinator for an existing Course.

Expected workflow:

Admin
    ↓
Faculty
    ↓
Academic Responsibilities
    ↓
Course Coordinator
    ↓
Select Course
    ↓
Assign
    ↓
Persist assignment
    ↓
Display assignment

The system must ensure:

- selected user is actually FACULTY
- selected Course exists
- assignment is persisted
- duplicate assignment is handled appropriately
- unauthorized users cannot perform the operation

If the existing academic design permits only one Course Coordinator per Course, enforce that rule.

If multiple coordinators are already supported by the existing architecture, preserve that behavior.

Do not guess.

Inspect existing models/design before deciding.

---

# 20. SUBJECT EXPERT ASSIGNMENT

Admin must be able to assign a Faculty member as Subject Expert for an existing Subject.

First inspect whether the repository already contains a Subject entity.

If Subject already exists:

Reuse it.

If an equivalent academic subject entity already exists under another name:

Reuse it.

Do NOT create a duplicate Subject model.

If the repository currently has NO Subject entity or equivalent:

Implement the smallest appropriate Subject representation required to support the assignment workflow.

Do not create unnecessary subject-management complexity.

The intended workflow is:

Admin
    ↓
Faculty
    ↓
Academic Responsibilities
    ↓
Subject Expert
    ↓
Select Subject
    ↓
Assign
    ↓
Persist assignment
    ↓
Display assignment

The system must ensure:

- selected user is FACULTY
- selected Subject exists
- assignment is persisted
- duplicate assignments are handled
- unauthorized users are rejected

---

# 21. FACULTY CAN HAVE BOTH RESPONSIBILITIES

The data model and UI must permit:

Faculty A
    ├── Course Coordinator → Course 1
    └── Subject Expert → Mathematics

and:

Faculty B
    ├── Subject Expert → Physics
    └── Subject Expert → Mathematics

where supported by the academic structure.

Do not design the system so that Course Coordinator and Subject Expert are mutually exclusive.

---

# 22. RESPONSIBILITY REMOVAL / REASSIGNMENT

Admin must be able to modify academic assignments.

Where supported, provide:

- remove Course Coordinator assignment
- change Course Coordinator
- remove Subject Expert assignment
- change Subject Expert

Use the existing database relationship design.

Do not leave orphaned assignment records.

If reassignment is performed, the UI should reflect the new assignment immediately after successful persistence.

---

# 23. COURSE DETAILS INTEGRATION

Extend the existing P0-007 Course Details page where appropriate.

Course Details should be able to display academic responsibility information, such as:

Course Coordinator:
    Faculty Name

Subject Experts:
    Faculty Name(s)

Only add this if the underlying Course/Subject relationships support it.

Do not duplicate Course Details functionality.

Maintain the existing SYS design.

---

# 24. FACULTY DETAILS INTEGRATION

Faculty Details should display:

System Role:
    FACULTY

Academic Responsibilities:

Course Coordinator:
    Course A
    Course B

Subject Expert:
    Mathematics
    Physics

Only show relationships that actually exist.

---

# 25. BACKEND API

Implement or complete the backend APIs required for:

Student Management
Faculty Management
Course Coordinator assignment
Subject Expert assignment

Use the repository's existing route conventions.

Possible conceptual operations include:

GET students
GET student
POST student
PUT/PATCH student
activate/deactivate student

GET faculty
GET faculty
POST faculty
PUT/PATCH faculty
activate/deactivate faculty

GET faculty responsibilities
POST course coordinator assignment
DELETE course coordinator assignment

POST subject expert assignment
DELETE subject expert assignment

IMPORTANT:

These are conceptual operations.

Use the actual existing route architecture.

Do NOT blindly create all of these endpoints if equivalent functionality already exists.

Do NOT duplicate endpoints.

---

# 26. BACKEND VALIDATION

Validate:

- user existence
- role correctness
- Course existence
- Subject existence
- duplicate accounts
- duplicate assignments
- invalid assignment targets
- authorization
- supported status values

A Course Coordinator assignment must not be assignable to a Student.

A Subject Expert assignment must not be assignable to a Student.

Only Faculty users can receive Faculty academic responsibilities.

---

# 27. DATABASE DESIGN

Inspect existing models before adding anything.

Prefer:

- existing User model
- existing role system
- existing Course model
- existing Subject model
- existing relationships

Only create new entities/relationships when genuinely required.

If new database structures are required:

1. Create the smallest appropriate models.
2. Follow existing SQLAlchemy conventions.
3. Create Alembic migration(s).
4. Preserve existing data.
5. Do not modify unrelated tables.

Do not use runtime table creation.

Do not create duplicate identity/account tables.

---

# 28. DATA INTEGRITY

Enforce appropriate database constraints where required.

Examples:

- unique user identifiers
- valid role relationships
- valid Course references
- valid Subject references
- prevention of duplicate responsibility assignments
- foreign key integrity

Do not rely exclusively on frontend validation.

---

# 29. AUTHORIZATION MATRIX

At minimum verify the following behavior.

## Students

Student:

- cannot access Admin Student Management
- cannot access Admin Faculty Management
- cannot create Faculty
- cannot create Student accounts
- cannot assign academic responsibilities

Expected result:

403

## Faculty

Faculty:

- cannot access Admin Student Management
- cannot access Admin Faculty Management
- cannot create Faculty accounts
- cannot create Student accounts
- cannot assign Course Coordinator
- cannot assign Subject Expert

Expected result:

403

## Admin

Admin:

- can manage Students
- can manage Faculty
- can assign Course Coordinators
- can assign Subject Experts
- can remove/reassign academic responsibilities

Expected result:

allowed

Use the actual authorization implementation from P0-004.

---

# 30. SYS BRANDING ASSET FAMILY — MANDATORY

All new frontend screens MUST use the established SYS Branding Asset family.

Before implementation inspect:

- SYS logo/brand assets
- typography
- colors
- theme
- buttons
- cards
- forms
- tables
- dialogs
- navigation
- dashboard components
- loading states
- empty states
- error states
- icons
- existing Course Management UI from P0-007

Reuse existing components.

Do NOT create a new visual language.

Do NOT invent:

- logos
- brand colors
- typography
- unrelated card styles
- unrelated buttons
- unrelated navigation

The new Student and Faculty screens must look like native SYS screens.

---

# 31. FRONTEND SCREENS

Implement the appropriate frontend routes/pages for:

Students
    ↓
Student List
Student Details
Create Student
Edit Student

Faculty
    ↓
Faculty List
Faculty Details
Create Faculty
Edit Faculty
Academic Responsibilities

Use the existing Next.js architecture.

Do not create a second routing system.

---

# 32. ADMIN NAVIGATION

Integrate Student and Faculty Management into the existing Admin navigation.

Do not create a separate dashboard/navigation framework.

Admin should have an intuitive path to:

Students
Faculty
Academic Responsibilities

Do not expose Admin-only navigation as usable functionality for Students or Faculty.

Backend authorization remains mandatory regardless of navigation visibility.

---

# 33. RESPONSIBILITY UI

Faculty Details should provide an Admin-facing academic responsibility management interface.

For example:

Faculty Details

    System Role
    FACULTY

    Academic Responsibilities

    Course Coordinator
    [Assigned Courses]

    Subject Expert
    [Assigned Subjects]

    [Assign Course]
    [Assign Subject]

Use existing SYS forms, dialogs, dropdowns, tables, and buttons.

Do not create a separate visual design system.

---

# 34. COURSE MANAGEMENT INTEGRATION

Extend P0-007 where required.

Course Details should be able to show:

Course Coordinator
Subject Experts

where the relationships exist.

Course creation/editing should NOT be unnecessarily redesigned.

If assignment is intentionally Admin-only, keep assignment controls restricted to Admin.

---

# 35. API INTEGRATION

Use the existing API client/configuration established by P0-006 and extended in P0-007.

Do not hardcode:

- localhost URLs
- production URLs
- API hostnames

Use the existing environment/configuration mechanism.

Use the existing authentication mechanism.

Do not introduce another HTTP client.

---

# 36. ERROR HANDLING

Handle:

400/422 → validation error
401 → authentication required/expired
403 → insufficient permissions
404 → Student/Faculty/Course/Subject not found
409 → duplicate/conflict
500 → server error

Use existing SYS error-handling patterns.

Do not expose internal stack traces.

---

# 37. LOADING / EMPTY / SUCCESS STATES

Every management page must appropriately handle:

Loading
Empty
Success
Validation error
Authorization error
Not found
Server error

Reuse existing SYS components.

---

# 38. RESPONSIVE DESIGN

Verify reasonable behavior on:

Desktop
Tablet
Mobile

Reuse the existing SYS responsive design system.

Do not redesign global responsive behavior.

---

# 39. ACCESSIBILITY

Use existing accessibility conventions.

At minimum:

- labels for form fields
- meaningful button names
- keyboard-accessible controls
- accessible dialogs
- readable validation messages
- semantic HTML where appropriate

---

# 40. BACKEND TESTS

Add/update tests for:

## Student Management

- Admin list students
- Admin view student
- Admin create student
- Admin update student
- Admin deactivate student where supported
- duplicate student handling
- validation
- unauthorized access

## Faculty Management

- Admin list faculty
- Admin view faculty
- Admin create faculty
- Admin update faculty
- Admin deactivate faculty where supported
- duplicate faculty handling
- validation
- unauthorized access

## Course Coordinator

- Admin assigns Faculty to Course
- Student cannot assign
- Faculty cannot assign
- non-existent Faculty rejected
- non-existent Course rejected
- duplicate assignment handled
- reassignment/removal works

## Subject Expert

- Admin assigns Faculty to Subject
- Student cannot assign
- Faculty cannot assign
- non-existent Faculty rejected
- non-existent Subject rejected
- duplicate assignment handled
- reassignment/removal works

---

# 41. FRONTEND VERIFICATION

Verify:

- Admin can open Students
- Admin can create Student
- Admin can edit Student
- Admin can deactivate Student where supported
- Admin can open Faculty
- Admin can create Faculty
- Admin can edit Faculty
- Admin can open Faculty Details
- Admin can assign Course Coordinator
- Admin can assign Subject Expert
- Admin can remove/reassign responsibilities
- Course Details reflect assignments where supported
- SYS branding is consistent

Verify Student and Faculty users cannot use Admin-only management operations.

---

# 42. END-TO-END VERIFICATION

The primary acceptance workflow is:

Login as Admin
    ↓
Open Students
    ↓
Create Student
    ↓
Student persists
    ↓
Student appears in list
    ↓
Edit Student
    ↓
Updated Student persists

Then:

Open Faculty
    ↓
Create Faculty
    ↓
Faculty persists
    ↓
Open Faculty Details
    ↓
Assign Course Coordinator
    ↓
Select Course
    ↓
Assignment persists
    ↓
Assign Subject Expert
    ↓
Select Subject
    ↓
Assignment persists
    ↓
Course Details reflect responsibility
    ↓
Faculty Details reflect responsibilities
    ↓
Remove/reassign responsibility
    ↓
UI reflects final state

Then verify:

Student account
    → Admin management rejected

Faculty account
    → Admin management rejected

Admin account
    → management allowed

Do not claim end-to-end verification unless actually performed.

---

# 43. NO UNRELATED REFACTORING

This is an end-to-end functional task.

Multiple backend/frontend files are expected.

However, do NOT refactor unrelated:

- authentication architecture
- authorization architecture
- Course CRUD
- unrelated APIs
- AI modules
- assessment modules
- deployment infrastructure
- global styling

unless directly required by this task.

If P0-007 Course components require a small reusable improvement, make the smallest appropriate change.

---

# 44. DEPENDENCY POLICY

Do not add dependencies unless genuinely necessary.

Before adding a dependency:

1. Check existing dependencies.
2. Reuse existing utilities.
3. Add only when no reasonable existing solution exists.
4. Keep dependency changes minimal.

Do not upgrade major frameworks/libraries.

---

# 45. MIGRATION POLICY

If database changes are required:

- create proper Alembic migration(s)
- preserve existing data
- test migration
- do not use runtime schema creation
- do not modify unrelated tables

If no migration is required, do not create one.

---

# 46. TOKEN EFFICIENCY

The goal is maximum functional implementation per Cursor task.

Do NOT spend significant tokens on:

- long explanations
- architecture essays
- repetitive summaries
- unnecessary documentation
- describing every changed line

Inspect → implement → test → verify → concise report.

Do not generate a long implementation report.

---

# 47. GIT SAFETY

Do NOT execute:

git reset --hard
git rebase
git filter-repo
git filter-branch
git push --force

Do not rewrite history.

Do not delete commits.

Do not commit automatically unless explicitly instructed.

Before completion:

git status

Do not modify unrelated uncommitted user work.

---

# 48. ACCEPTANCE CRITERIA

## Student Management

- [ ] Admin can list students.
- [ ] Admin can view student details.
- [ ] Admin can create students.
- [ ] Admin can edit students.
- [ ] Existing activation/deactivation mechanism is supported where applicable.
- [ ] Student accounts use the existing STUDENT role.
- [ ] Authentication architecture is reused.
- [ ] Sensitive authentication data is never exposed.

## Faculty Management

- [ ] Admin can list faculty.
- [ ] Admin can view faculty details.
- [ ] Admin can create faculty.
- [ ] Admin can edit faculty.
- [ ] Existing activation/deactivation mechanism is supported where applicable.
- [ ] Faculty accounts use the existing FACULTY role.

## Academic Responsibilities

- [ ] Course Coordinator responsibility is supported.
- [ ] Subject Expert responsibility is supported.
- [ ] Academic responsibilities are not incorrectly implemented as system roles.
- [ ] Faculty can hold both responsibilities.
- [ ] Admin can assign Course Coordinators.
- [ ] Admin can assign Subject Experts.
- [ ] Admin can remove/reassign responsibilities.
- [ ] Invalid assignments are rejected.
- [ ] Duplicate assignments are handled.

## Course Integration

- [ ] Existing P0-007 Course Management remains functional.
- [ ] Course Coordinator information is available where supported.
- [ ] Subject Expert information is available where supported.
- [ ] Course Details reflects academic assignments where applicable.

## Authorization

- [ ] Unauthenticated Admin operations return 401.
- [ ] Students receive 403 for Admin management operations.
- [ ] Faculty receive 403 for Admin management operations.
- [ ] Admin receives appropriate access.
- [ ] Backend remains authoritative.

## Frontend

- [ ] Student management screens implemented.
- [ ] Faculty management screens implemented.
- [ ] Academic responsibility UI implemented.
- [ ] Admin navigation integrated.
- [ ] Existing API client reused.
- [ ] Loading/empty/error states implemented.
- [ ] Responsive behavior follows SYS conventions.
- [ ] Accessibility conventions followed.

## SYS Branding

- [ ] SYS Branding Asset family inspected.
- [ ] Existing SYS logo/brand assets reused.
- [ ] Existing colors/theme preserved.
- [ ] Existing typography preserved.
- [ ] Existing UI components reused.
- [ ] Student screens match existing SYS UI.
- [ ] Faculty screens match existing SYS UI.
- [ ] Academic responsibility screens match existing SYS UI.
- [ ] No parallel design system introduced.

## Testing

- [ ] Student backend tests pass.
- [ ] Faculty backend tests pass.
- [ ] Responsibility assignment tests pass.
- [ ] Authorization tests pass.
- [ ] Frontend verification passes.
- [ ] End-to-end workflow passes.

---

# 49. BLOCKER POLICY

Resolve ordinary implementation problems within this task.

Do not stop because a missing CRUD operation, schema, relationship, API, frontend component, validation rule, or test needs to be implemented.

Stop and report only if the issue requires a major architectural decision such as:

- authentication redesign
- authorization redesign
- complete database architecture redesign
- frontend framework replacement
- backend framework replacement
- destructive migration
- fundamental API redesign

For normal missing functionality, implement it.

---

# 50. FINAL RESPONSE TO PROJECT OWNER

Do NOT provide a long report.

Return ONLY:

Files changed:
<list>

Student management:
PASS / FAIL

Faculty management:
PASS / FAIL

Course Coordinator assignment:
PASS / FAIL

Subject Expert assignment:
PASS / FAIL

Authorization verification:
PASS / FAIL

SYS branding verification:
PASS / FAIL

Backend tests:
PASS / FAIL

Frontend verification:
PASS / FAIL

End-to-end verification:
PASS / FAIL / NOT POSSIBLE

Database migration:
YES / NO

Remaining blocker:
<None or concise description>

Do not repeat this task specification.

Do not provide a long architectural explanation.

---

# 51. FINAL IMPLEMENTATION INSTRUCTION

This task is a **major functional SYS feature**.

Do not treat it as:

- a configuration task
- an audit
- a documentation task
- a simple User CRUD task

Implement the complete Admin academic-management workflow.

The intended result is:

Admin
    ↓
Student Management
    ↓
Faculty Management
    ↓
Academic Responsibility Management
    ↓
Course Coordinator
    ↓
Subject Expert
    ↓
Course integration

Use the existing SYS architecture from P0-001 through P0-007.

Do not recreate existing Course Management.

Do not redesign authentication.

Do not redesign authorization.

Do not create a parallel frontend design system.

Maximize actual functionality delivered per Cursor task.

Minimize explanation, documentation, and unnecessary refactoring.

The feature is complete only when the Admin can actually manage Students, Faculty, Course Coordinator assignments, and Subject Expert assignments through the SYS frontend and the changes persist correctly through the backend/database.