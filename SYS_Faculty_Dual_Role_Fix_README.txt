SYS Faculty Dual-Role and Draft-Syllabus Fix
=============================================

Apply from the repository root (D:\sys-ai-powered-learning-system):

  Expand-Archive -Path "$HOME\Downloads\SYS_Faculty_Dual_Role_Draft_Syllabus_Fix.zip" -DestinationPath . -Force

No database migration is required.

Expected pilot result for Dr. B Sudhakar:
- Assigned Courses: 1 (TGPCPWT-2026)
- Assigned Subjects: 2 (English and Arithmetic)
- Course coordinator sees the complete configured eight-subject draft syllabus.
- A subject expert without coordinator responsibility sees only assigned branches.
- Students cannot see draft/unpublished syllabus content.
- Draft topics cannot launch learning sessions before final approval.

Verification:

Backend (with the backend virtual environment active):
  cd backend
  python -m unittest tests.test_subject_syllabus_workflow tests.test_phase_d_workspace tests.test_phase_a_auth_access tests.test_syllabus_configuration tests.test_course_publication

Frontend:
  cd ..\frontend
  node --test tests/role-dashboard-layout.test.mjs tests/syllabus-management-navigation.test.mjs tests/course-enrollment.test.mjs tests/syllabus-review.test.mjs
  npm run build

