# SYS syllabus upload, review and approval

Apply this patch after the complete Phase E AI Lecturer patch. It introduces migration
`20260828_p028_syllabus` after `20260827_p027_ai_gateway`.

## Install safely

1. Stop backend and frontend. Back up the PostgreSQL database and preserve your current Git changes.
2. From the repository root:

```powershell
cd D:\sys-ai-powered-learning-system
git apply --check "$HOME\Downloads\SYS_Syllabus_Upload_Review_and_Approval.patch"
git apply "$HOME\Downloads\SYS_Syllabus_Upload_Review_and_Approval.patch"
cd backend
python -m alembic upgrade head
```

Use your existing backend virtual environment. No additional application dependencies,
provider configuration changes, or encryption-key rotation are required. The application
continues using its configured `SECRET_KEY` to sign workbook references.

The migration adds ordering fields, unit learning outcomes, review records and immutable
approved snapshots. Existing academic identifiers and learning records are preserved.
It does **not** silently approve existing syllabuses. Downgrade is deliberately blocked to
prevent deletion of approval history; restore a verified database backup for rollback.

## First syllabus / existing-course baseline

1. Create the course as Draft and assign its course coordinator through Academic responsibilities.
2. Administrator: **Course Master > Course > Manage syllabus**.
   Coordinator: **Courses > Course workspace > Review syllabus / coordinator approvals**.
3. Select **Start new review**. Existing subjects/units/topics/subtopics become the draft baseline.
4. For a new course, add items on screen, or expand **Excel upload** and download the blank template.
5. Fill **Subjects, Units, Topics, Subtopics**. Descriptions occur once at their own level.
   Use a positive order number within each parent. Parent dropdowns use readable full paths.
   Keep row 1 headers and hidden references unchanged. No hierarchy codes are required.
6. Upload the workbook, review validation errors or the before/after preview, and choose
   **Accept into draft**. This changes the screen only. **Save draft** persists the proposal.
7. Enter a review summary, then **Save & submit for approval**.
8. The coordinator reviews the complete proposal, enters a decision reason and chooses
   **Approve complete proposal**. Coordinators can approve their own course-wide setup;
   administrator overrides are recorded in the audit trail.
9. Revision 1 is now available as an approved PDF. Assign subject experts to the approved
   subjects, configure academic weightages separately, and complete the existing publication process.

Syllabus approval does not publish a course. Publication readiness now requires an approved
syllabus version. Existing published courses are not automatically unpublished by migration;
their approved PDF becomes available after baseline approval.

The old flat pilot workbook is not the new template. Download a workbook from the actual
course review before populating it; its metadata binds it to that draft. Upload limits are
3 MB and 5,000 total items. The file contains Instructions and four editable data sheets,
plus hidden SYS metadata. Sheet protection is an accidental-edit safeguard, not security.

## Subject-expert updates

1. Open the assigned course workspace and select **Review syllabus / coordinator approvals**.
2. Select an assigned subject and **Start new review**.
3. Expand a unit/topic. Add or edit topics/subtopics, edit descriptions, or use Move up/down.
   Subjects and units are read-only. Excel upload/download is not offered to subject experts.
4. Save the draft, supply a reason and submit. Until submission, the draft is private to its author.
5. The assigned active coordinators receive in-app and email delivery records through the
   existing Notification Engine. Open the notification to review the proposal.
6. The coordinator can approve the complete proposal, request changes with comments, or reject.
   A returned proposal can be revised and resubmitted. Submitted proposals are locked;
   the author may withdraw one for editing before a decision.
7. The submitting faculty member is notified of the decision. Approval updates the live
   syllabus in one transaction and creates the next immutable approved version.

The initial whole-course baseline must be approved before a subject-only proposal can be
approved. Subject-only faculty proposals cannot be self-approved by a faculty member who
subsequently becomes a coordinator; another coordinator or audited administrator decides.

## Downloads and academic history

- Approved course PDF: course profile, faculty reports, course learning workspace and review page.
- Approved subject PDF: subject sections in the course workspace and existing subject report actions.
- Historical approved versions: review page > Approved version history.
- Students require active learning access to a published course. Pending/unavailable enrollment
  does not grant download access. Experts receive only their assigned subject content.
- PDFs include SYS logo, blue/royal-purple header, tagline, course identity, revision number,
  approval attribution, dates, descriptions, unit learning outcomes and page numbers.
- Academic weightages remain a separate configuration and are not silently invented or included
  as part of a syllabus approval. Course/subject profile reports still show their configured weights.
- Renaming or reordering preserves existing IDs, questions, assessment versions and learning history.
- Content changes mark saved lectures in the affected subject for academic verification. The
  classroom displays a warning; no AI regeneration or student-completion reset occurs automatically.

## Conflict and safety rules

- Damaged/duplicate SYS references, invalid parents, duplicate sibling names and newly introduced
  duplicate order numbers are rejected. Existing legacy ordering ties may remain unchanged.
- New rows have blank references; the preview identifies additions explicitly.
- Omitted workbook rows leave existing draft items unchanged. Removing a newly added draft item
  is available on screen. Existing approved items cannot be deleted through this workflow.
- Cross-parent moves and retirement/deletion are intentionally blocked; they need a separate
  dependency-aware administrative process. There is no partial approval.
- Saving a draft invalidates older workbook versions. Download a fresh workbook after saving.
- A newer course approval makes older proposals stale, even for a different subject. Create a new
  review and reconcile the old comparison manually. There is no silent merge or automatic overwrite.
- Once the course enters review governance, legacy direct syllabus mutation endpoints are blocked.
  Their old bootstrap behavior remains only for courses that have never entered review governance.
- Archived courses are read-only. Permissions and author assignments are rechecked on approval.

Email needs the existing working SMTP configuration. A missing/failed SMTP service is recorded
by the notification engine; it does not undo approval. In-app delivery remains available.
Notification records are created atomically with submission/decision; delivery occurs after commit.
Use the existing administrator notification dispatch/retry controls for failed or pending deliveries.
No live email or provider request was used during implementation verification.

## Verification

```powershell
cd D:\sys-ai-powered-learning-system\backend
$env:TEST_DATABASE_URL = "sqlite:///:memory:"
python -m unittest tests.test_syllabus_review tests.test_courses tests.test_pending_enrollment tests.test_ai_management tests.test_ai_lecturer tests.test_phase_d_workspace tests.test_course_profile_pdf tests.test_course_publication tests.test_course_syllabus_structure -v

cd ..\frontend
node --test tests/syllabus-review.test.mjs tests/syllabus.test.mjs tests/course-reports.test.mjs tests/phase-e-lecturer.test.mjs tests/ai-provider.test.mjs tests/phase-d-workspace.test.mjs
npm run build
```

Restart both applications after migration and build. Verify with separate administrator,
coordinator, subject-expert and student accounts:

1. Import a small initial syllabus, preview and approve revision 1.
2. Download and open the workbook in the institution's Excel/LibreOffice version; verify dropdowns
   and edit/save/re-upload. Desktop spreadsheet interoperability should be checked locally.
3. Faculty adds a subtopic; verify it is absent from the student's syllabus before approval.
4. Coordinator requests changes, faculty resubmits, then coordinator approves.
5. Verify scoped notifications, revision 2 PDF, old revision 1 PDF and preserved learning records.
6. Confirm an unrelated faculty member, pending student, damaged workbook reference and stale
   proposal are rejected. Check desktop and mobile layouts in your actual browser.

The implementation was checked with isolated backend tests, frontend logic/source tests,
simulated React interactions, workbook round-trip validation and rendered PDF/workbook QA.
Full Next.js build, real-browser end-to-end testing and live SMTP delivery require your complete
local environment. The supplied source snapshot does not include the full frontend runtime/assets.
