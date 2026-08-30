# SYS saved syllabus configuration fix

Apply after the Subject Review, Reset and Branded Syllabus PDF patch (p029).
No migration, reset or workbook re-upload is required.

## What changes

- Course Master and course profiles show saved working syllabus counts immediately.
- Academic Responsibilities uses the same saved subjects and expert assignments as Reviews & Approvals.
- Existing uploaded drafts and existing draft expert assignments are recognized automatically.
- Saved draft keys remain stable; they are not temporary row numbers or renamed subjects.
- Draft content does not replace approved learning content. Only the existing approval workflow materializes live syllabus records.
- The expert selector lists eligible faculty master records with employee code, department, and registration-pending labels.
- Pending-registration faculty can be assigned, but cannot receive a review request until registered and active.
- An assigned review expert is shown with a Change expert action. Active reviews must be finished or invalidated before reassignment.
- Course profile PDFs show saved syllabus counts, ownership and working-syllabus status.
- Student access, final-approval separation and publication checks remain enforced.

## Verify

From the repository root:

```powershell
cd backend
$env:TEST_DATABASE_URL = "sqlite:///:memory:"
python -m unittest tests.test_syllabus_configuration tests.test_syllabus_review tests.test_course_publication tests.test_courses tests.test_course_profile_pdf -v
cd ..\frontend
node --test tests/syllabus-configuration.test.mjs tests/subject-syllabus-workflow.test.mjs tests/syllabus-review.test.mjs tests/syllabus.test.mjs tests/course-reports.test.mjs
npm run build
```

Retain the previously corrected `Download syllabus PDF` assertion in course-reports.test.mjs.
Restart backend/frontend after applying, then refresh Course Master.

## Pilot checks

1. Open the existing course: the saved eight subjects should be counted, without re-uploading.
2. Open Academic Responsibilities and select this course: the saved subjects and existing English expert should appear.
3. Assign another subject expert, then open Reviews & Approvals: the assignment must match.
4. Pending-registration faculty must be visibly labelled and unable to receive a review request.
5. Assign a registered active faculty member and request review; verify the correct recipient receives the notification.
6. Download the course profile PDF and a subject syllabus PDF: confirm counts, ownership and approval status.
7. Confirm students cannot access the unpublished syllabus.

When a live subject already has multiple academic experts, the review page selects the designated reviewer. Adding that reviewer preserves other academic responsibilities; it does not silently remove other experts.
