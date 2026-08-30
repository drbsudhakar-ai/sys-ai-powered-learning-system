# P0-021 — Super Admin Operations Dashboard V2
## Execution baseline and corrections

- Start from exact HEAD:
  `2122e59a105dd6406be5441a5d38cb5ad794abf0`
- P0-020, P0-020.1 and P0-020.2 are complete.
- Explicit `super_admin` authorization is already implemented and tested.
- Do not re-audit, redesign or reimplement authentication/role hierarchy.
- Do not modify registration, OTP recovery, bootstrap or session invalidation unless a direct regression caused by this task is proven.
- Existing `/admin/students` and `/admin/faculty` pages are the baseline. Refactor and enhance them; do not create competing pages.
- All backend tests must use the isolated test database introduced by P0-020.1.
- Record development-database row counts before and after tests; they must remain unchanged.
- Do not reset or populate the development database during this task.


Implement the frozen Super Admin dashboard design. Focus on implementation, tests and build. Avoid broad audits and long reports.

## Safety

- Read applicable `AGENTS.md` and `CLAUDE.md`.
- Start from completed P0-020.
- Preserve unrelated dirty/untracked files.
- Do not modify Homepage V2 or replace frozen branding assets.
- Use only real APIs and existing routes. Never invent metrics, activities or links.
- Do not push.

## 1. Authorization

Use the explicit role hierarchy:

`super_admin > admin > faculty > student`

- `super_admin` inherits every `admin` permission.
- Only Super Admin can access administrator-account, security, audit and platform-setting functions.
- Institution Admin manages institution-scoped students, faculty and academic operations.
- Public registration must never create `admin` or `super_admin`.
- The secure bootstrap command must create `super_admin`.
- If P0-020 has not completed this hierarchy, add the minimum backend migration, authorization changes and regression tests.
- Do not expose dashboard content until `/auth/me` confirms an active authorized user.
- Redirect unauthorized users safely without briefly rendering the shell.

## 2. SYS branding

Use canonical assets only from:

`frontend/public/branding/sys-v2/`

Apply branding appropriately:

- Frozen SYS header logo in the expanded sidebar.
- Compact SYS symbol in collapsed/mobile navigation.
- Brand tokens from `tokens/sys-brand.css`.
- Navy navigation, light neutral workspace, blue primary actions, purple secondary accents and limited gold warnings.
- Branded loading, empty and error states using the compact symbol.
- Preserve image aspect ratios; never stretch or crop logos.
- Accessible alt text where meaningful; decorative marks use empty alt text.
- Sidebar footer:

  `SYS — Strengthen Your Skills`  
  `Shape Your Successful Future.`  
  `© {current year} SYS`

- Use a dynamic year.
- Do not add a full global footer to the dashboard.
- Avoid neon glow, oversized logos, glass effects or distracting watermarks.
- Create reusable brand-state components if useful for future dashboards.

## 3. Admin shell

Refactor the existing `AdminShell` rather than creating a competing layout.

### Desktop

- Expandable/collapsible dark sidebar.
- Light main workspace.
- Sticky compact top bar.
- Persist sidebar collapsed state locally.
- Current route clearly highlighted.

### Tablet/mobile

- Tablet icon sidebar.
- Mobile drawer with overlay.
- Close using Escape, overlay click or navigation.
- Restore focus to the menu button.
- Prevent background scrolling while open.

### Top bar

Include:

- Sidebar toggle
- Breadcrumb/page title
- Real institution/scope label when available
- Notification button with real unread count
- Profile menu with name and role
- Logout

Do not add global search until searchable backend functionality exists.

Use accessible disclosure buttons with `aria-expanded`, `aria-controls` and keyboard operation.

## 4. Expandable navigation

Use grouped navigation. Render only links whose routes actually exist and which the current role may access. Omit unavailable modules instead of creating broken links.

- Overview
- People & Access
- Academic Management
- Learning & Assessment
- Intelligence & Student Support
- Communication & Reports
- System Administration

Map existing verified routes into these groups, including current student/faculty management, courses, assessments, learning sessions, analytics, learning journey, performance and notifications.

Only Super Admin sees Super Admin-specific navigation.

Keep no more than one navigation group expanded automatically; always keep the group containing the active route expanded.

## 5. Overview screen

### Welcome header

Show real profile data:

`Good morning/afternoon/evening, {name}`

Badges:

- `Super Admin` or `Institution Admin`
- Real institution/scope when available

Do not hardcode a person or institution.

### Quick actions

Show only actions with working routes and permissions:

- Add/upload students
- Add/upload faculty
- Create programme
- Assign academic responsibility
- Send notification

Omit an action if its route/functionality does not exist.

### Attention required

Build actionable items only from validated API data:

- Pending account activations
- Inactive or incomplete master records
- Programmes without coordinators
- Subjects without experts
- Failed notification deliveries
- Students requiring attention when supported by analytics

Each item links to a valid destination. If the supporting endpoint is absent or malformed, display `Unavailable`, not zero or “all clear.”

### Summary cards

Limit the main row to four cards:

1. Students — total, active, pending activation
2. Faculty — total, active, pending activation
3. Programmes — active and draft
4. Attention Required — real actionable total

Every card must show loading, unavailable and available states distinctly.

### Setup & Operational Readiness

Create an accessible expandable task-list section:

- Institution profile configured
- Student/faculty masters available
- Registration contacts available
- Programmes created
- Subjects configured
- Coordinators and experts assigned
- Syllabus structure configured
- Question intelligence available
- Learning/assessment operations ready
- Notification delivery configured

Use only exact predicates supported by available data:

- `Complete`
- `Needs attention`
- `Unavailable`

Do not mark the whole system complete because one record exists.

### Operational panels

Include when backed by real APIs:

- Academic Operations
- Recent Assessments/Learning Sessions
- Early Warning Summary
- Recent Administrative Activity

If audit/activity APIs do not exist, show a concise unavailable state and do not fabricate events.

## 6. Course responsibility

Reflect this ownership:

- Super Admin/Admin: create, edit, activate, archive and restore programmes; assign coordinators and experts.
- Course Coordinator: configure assigned course structure and monitor delivery.
- Subject Expert: manage assigned subject content, questions and assessments.

Course creation should remain draft until required academic configuration is complete.

## 7. Data handling

- Load dashboard data only after authorization succeeds.
- Avoid duplicate requests.
- Validate collection responses and required consumed fields.
- A malformed successful response is `Unavailable`, not an empty array.
- Any authenticated dashboard request returning 401 must clear the session and redirect to `/login?reason=expired`.
- Use abort/cancellation protection when leaving the page.
- Provide a manual refresh action and real last-updated time.
- Never display fake percentages or unsupported trend comparisons.

## 8. Responsive and accessibility acceptance

Verify at 1440px, 768px and 390px:

- No horizontal page overflow.
- Cards change 4 → 2 → 1 columns.
- Tables adapt without clipping important actions.
- Drawer/sidebar keyboard behaviour works.
- Visible focus states and adequate touch targets.
- No duplicate global header, footer or main.
- Exactly one admin top bar and one main landmark.
- Semantic headings and accessible status labels.
- Reduced-motion preference respected.

## API compatibility

Existing admin collection endpoints may currently return arrays and are consumed by existing screens.

- Inspect every frontend/backend consumer before changing a response contract.
- Do not silently replace an existing array response with `{ items, total, page, page_size }`.
- Either:
  1. Add dedicated paginated management endpoints, or
  2. Update every consumer atomically with regression tests.
- Prefer dedicated paginated endpoints when that provides safer backward compatibility.
- Search, filtering and sorting must occur before pagination.
- Use allowlists for sortable/filterable fields.


- Reuse existing detail and edit routes.
- A read-only preview drawer is optional when useful.
- Do not create a second competing editing interface inside a drawer.


- Master Upload and Import History are shown only if working APIs/routes exist.
- Do not implement the complete import engine inside P0-021.
- Do not extend the Course domain merely to satisfy dashboard wording.
- Represent existing course capabilities accurately; defer unsupported lifecycle operations.
- When profile name or institution data is unavailable, use a neutral fallback such as `Welcome back`; do not invent a name or institution.


- Apply SYS branding to export filenames and formats that support visual branding.
- Do not insert decorative branding rows into machine-readable CSV files.
- Sanitize spreadsheet-formula values in CSV exports.



## 9. Verification

Run:

- Focused backend authorization tests if backend changes were required.
- Complete existing backend suite.
- Frontend production build.
- Browser verification for `/admin-dashboard` with Super Admin, Admin, Faculty, Student, expired and inactive sessions.
- Browser console check.
- Canonical brand-asset loading and aspect-ratio check.
- Existing homepage and login smoke checks.
- `git diff --check`.

## Commits

Create exactly two focused commits after verification:

1. Backend APIs, validation, audit support and tests:

   `feat(admin): add student and faculty master management APIs`

2. Admin dashboard and master-management UI:

   `feat(admin): build SYS operations and master workspaces`

Before each commit:

- Inspect the complete diff.
- Stage only task-related files.
- Run `git diff --cached --check`.
- Confirm no unrelated files or deletions are staged.
- Do not amend previous commits or push.

Return only:

- Commit SHAs
- Focused/full backend test totals
- Development database row counts before/after tests
- Frontend build result
- Browser verification result
- Genuine unavailable capabilities


## Student and Faculty Master Management

Implement dedicated `/admin/students` and `/admin/faculty` workspaces.

- Keep dashboard cards as summaries linking to these pages.
- Add server-side search, filters, sorting and pagination.
- Do not download every record and process it in the browser.
- Validate sortable/filterable fields against server-side allowlists.
- Return `{ items, total, page, page_size }`.
- Persist table state in URL query parameters.
- Use semantic sortable tables with `aria-sort`.
- Provide responsive record cards on mobile.
- Add expandable filter panels.
- Add status tabs: All, Pending Registration, Active, Inactive, Needs Attention.
- Add record-detail/edit drawers.
- Add permission-controlled bulk actions with confirmation and audit.
- Never hard-delete records linked to academic history.
- Add Upload Master, Download Template, Add Individual, Import History and Export Current View actions only when their routes/APIs exist.
- Apply SYS branding to tables, state indicators, empty/error states and exported files.
- Mask mobile numbers in list views.
- Use real registration, verification and last-login data; show `Unavailable` when unsupported.
- Add backend pagination/search/filter/sort tests and frontend keyboard/responsive verification.


## Master Management Testing

### Backend tests

Add focused tests covering:

- Super Admin and Admin can access permitted master records.
- Faculty and Student receive 403.
- Inactive/expired sessions are rejected.
- Search by:
  - Roll number/employee code
  - Name
  - Email
  - Mobile
- Student filters:
  - Programme
  - Admission year
  - Present year
  - College
  - Registration status
  - Academic status
- Faculty filters:
  - College
  - Department
  - Designation
  - Registration status
  - Employment status
  - Coordinator/Subject Expert assignment
- Every supported sortable column in ascending and descending order.
- Invalid sort/filter fields are rejected through server-side allowlists.
- Sorting and filtering apply to the complete dataset before pagination.
- Pagination boundaries, total count and empty results.
- Email and mobile normalization.
- Duplicate roll numbers, employee codes, verified emails and personal mobile numbers.
- Individual update authorization and validation.
- Bulk activate/deactivate and assignment operations.
- Partial bulk failures return per-record errors without hiding successful changes.
- Records linked to academic history cannot be hard-deleted.
- Every update and bulk operation creates an audit entry.
- Malformed requests do not expose database or personal information.
- Export includes only the authorized filtered dataset.
- If CSV export is implemented, neutralize spreadsheet-formula cells beginning with `=`, `+`, `-` or `@`.
- Existing backend tests continue passing.

### Frontend tests/browser verification

Verify:

- Search debounce, submission and clear behaviour.
- Filters combine correctly and can be reset.
- Sort indicators and `aria-sort` update correctly.
- Search/filter/sort/page state persists in URL parameters.
- Changing search/filter/sort returns to page 1.
- Pagination and 25/50/100 page-size selection.
- Status tabs show correct filtered results.
- Record drawer opens, closes with Escape and restores focus.
- Edit validation and success/error states.
- Bulk selection, select-current-page behaviour and confirmation dialog.
- Bulk result summary clearly reports successes and failures.
- Mobile numbers are masked in list views.
- Loading, empty, no-results, unavailable and error states are distinct.
- Student and Faculty routes work at 1440px, 768px and 390px.
- Mobile uses readable record cards without horizontal page overflow.
- Keyboard navigation and visible focus states work.
- SYS branding assets load without distortion.
- No duplicate header, footer or main.
- Browser console contains no warnings/errors.
- Homepage, login and admin-dashboard smoke tests pass.
- Production Next.js build passes.
- Run `git diff --check`.

## Commit instructions

Create focused commits only after all relevant verification passes.

1. Only if Super Admin hierarchy was not already completed by P0-020:

   `feat(auth): formalize super admin authorization`

2. Backend master-management APIs, validation, migration and tests:

   `feat(admin): add student and faculty master management APIs`

3. Admin dashboard, Student Master and Faculty Master UI:

   `feat(admin): build SYS operations and master management workspaces`

Before each commit:

- Inspect `git diff`.
- Stage only files belonging to that commit.
- Confirm no unrelated documentation, shared-layout work or legacy branding directories are staged.
- Confirm no deletions are staged unless explicitly required by this task.
- Run `git diff --cached --check`.
- Inspect `git diff --cached --stat`.

Do not amend previous commits, squash unrelated work or push.

Return only:

- Commit SHA(s)
- Focused/full backend test totals
- Frontend production-build result
- Browser verification result
- Any genuinely unavailable API/provider functionality