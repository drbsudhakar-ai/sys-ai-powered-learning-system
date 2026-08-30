# SYS - Subject syllabus review, reset and print verification

Apply this patch after the corrected Excel Upload Progress and Drag Drop patch.
The workbook format is unchanged. Existing saved syllabus content is retained.

## Installation

1. Stop the backend and back up the PostgreSQL database.
2. Apply the patch from the repository root using `git apply --check`, then `git apply`.
3. In the activated backend environment run `python -m alembic upgrade head`.
   The new migration is `20260828_p029_subject_review`, following p028.
4. Restart the backend and frontend.

The migration retains approved snapshots and saved draft content. Unfinished
course-wide submissions return to Draft for subject-wise review. Legacy
self-started subject proposals are retained as Cancelled; their content is not
deleted and can be reconciled by the coordinator. New faculty review work is
created only through a manager's explicit request.

## Initial pilot workflow

1. Admin or assigned course coordinator saves the full syllabus in Syllabus
   Structure or Excel Upload.
2. Use **Download complete syllabus PDF** for physical verification. The PDF
   identifies the exact saved version and its approval status.
3. Open **Reviews & Approvals**. Assign an active subject expert for each draft
   subject, then click **Request review**. Existing live subjects must already
   have their faculty assigned through Academic Responsibilities; the reviewer
   selector offers only those assigned people.
4. The expert receives an in-app/email notification with a direct subject-review
   link. They can download their subject PDF, add/edit/reorder topics and
   subtopics, and enter comments for subject/unit changes outside their scope.
5. The expert chooses **Recommend approval without changes** or **Submit
   proposed changes**. Unsaved recommendations cannot be downloaded as a saved PDF.
6. A different administrator or assigned coordinator compares changes and
   finally approves the subject, or returns it with comments. The subject expert
   cannot grant final approval to their own recommendation, even if also a CC.
7. After all subjects are finally approved, an initial unpublished course gets
   an approved syllabus revision and live academic IDs. Draft-subject faculty
   assignments become ordinary SubjectExpertAssignments.
8. Complete existing course readiness checks (coordinator, weightages, etc.),
   then use the existing administrator publication action on the course profile.
   Final syllabus approval does not automatically publish the course.

## Published courses and later corrections

The published syllabus stays active while a replacement is reviewed. A new
working version carries forward unchanged subjects' approvals. Editing a
subject invalidates only that subject's review and notifies its reviewer.
Request a new review for the changed subject. All subject approvals are checked
again before publication. Existing lessons, assessment references and student
history are retained; affected saved lessons are flagged for academic review.

The existing course publication permission remains administrator-only. This
patch does not broaden that permission to faculty coordinators.

## Clear unapproved syllabus

On **Syllabus Structure > Advanced actions**, admin or assigned CC can clear an
unapproved working syllabus. Enter the exact course code and a reason. If any
requests are active, explicitly confirm cancellation; reviewers are notified.

Clearing is blocked for any final subject approval, approved course version,
published course, existing live academic hierarchy, learning session or
assessment. The clear operation never deletes those records.

Before clearing, the complete working content is preserved in a
`syllabus.reset_snapshot` audit entry. Recovery is an administrator-assisted
operation from that snapshot; a self-service Restore button is not included.
Download a fresh template after clearing: old workbook version tokens are
intentionally invalidated.

## PDFs and navigation

* Three pages remain: Syllabus Structure, Excel Upload, Reviews & Approvals.
* The old Approved Syllabus page redirects to the role-appropriate course page.
* Version history and approved downloads live under Reviews & Approvals.
* Admin/CC can print full or individual subject syllabus copies before approval.
* Experts can print only their assigned subject review copies.
* Students can download only published versions, with normal enrollment checks.
* PDFs use the canonical SYS logo, Blue-Royal Purple branding, course code,
  saved version, IST timestamp, per-subject reviewer/approver details, page
  numbers and status on every page. Draft copies include review-note space.
* Status distinguishes Draft, Under Review, Expert Review Completed,
  Partially Approved, Approved-Not Published, and Approved and Published.
* Existing historical versions without subject-review metadata do not invent
  reviewer details. Only an exact-version publication record earns the published
  label. A legacy version with uncertain publication timing needs explicit
  republication before student PDF access.

## Verification

Backend tests use disposable SQLite, never the development database:

```powershell
cd backend
$env:TEST_DATABASE_URL = "sqlite:///:memory:"
# pypdf is needed only for the PDF assertions if not already installed.
python -m pip install pypdf
python -m unittest tests.test_subject_syllabus_workflow tests.test_syllabus_review tests.test_course_publication -v
cd ..\frontend
node --test tests/syllabus*.test.mjs tests/subject-syllabus-workflow.test.mjs
npm run build
```

Validated here: isolated subject workflow, workbook validation, migration data
preservation, notification recipient selection/rollback, publication staging,
reset safeguards, frontend source contracts, and rendered PDF layout.

Full Next.js build/browser tests and actual SMTP delivery remain local checks.
The broader existing learning suites could not run in this test environment
because its cached bcrypt 5 / Passlib combination failed during authentication
fixture setup. No authentication or password-handling code was changed.

Before the pilot, smoke-test one subject as admin, assigned expert and CC; check
the in-app notification, print a draft PDF, submit a changed topic, return it
once, finally approve it, and confirm that publication remains blocked while
another subject is still pending. Also test a wrong-file reset on a disposable
draft course, not your approved pilot.
