"""P0-021 administrator master-management API regression tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import isolation as _test_isolation  # noqa: E402,F401
from fastapi.testclient import TestClient  # noqa: E402

from app import database, models, utils  # noqa: E402
from app.main import app  # noqa: E402
from tests.auth_helpers import ProtectedUserFactory  # noqa: E402


client = TestClient(app)
users = ProtectedUserFactory(client, "P021")


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class AdminMasterManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = users.create("admin", {"employee_code": "P021-ADMIN"})
        cls.faculty = users.create("faculty", {"employee_code": "P021-FAC"})
        cls.student = users.create("student", {"roll_number": "P021-STU"})
        cls.super_token = cls._create_login_user("super_admin", "P021-SUPER")

    @classmethod
    def _create_login_user(cls, role: str, code: str) -> str:
        email = f"{code.lower()}_{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPass123!"
        with database.SessionLocal() as db:
            user = models.User(
                name=code,
                email=email,
                institutional_email=email,
                email_verified=True,
                hashed_password=utils.hash_password(password),
                role=role,
                employee_code=code.upper(),
                is_active=True,
                account_status="ACTIVE",
                session_version=1,
            )
            db.add(user)
            db.commit()
        response = client.post("/auth/login", data={"username": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    def _student(self, **overrides) -> dict:
        suffix = uuid.uuid4().hex[:10]
        payload = {
            "name": f"Student {suffix}",
            "roll_number": f"S-{suffix}",
            "email": f"student_{suffix}@example.com",
            "mobile_number": f"+9198{int(suffix[:8], 16) % 100000000:08d}",
            "college": "SYS College",
            "admission_year": 2026,
            "present_year": 1,
            "academic_status": "ACTIVE",
            **overrides,
        }
        response = client.post("/admin/students", headers=auth(self.admin.token), json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _faculty(self, **overrides) -> dict:
        suffix = uuid.uuid4().hex[:10]
        payload = {
            "name": f"Faculty {suffix}",
            "employee_code": f"F-{suffix}",
            "email": f"faculty_{suffix}@example.com",
            "mobile_number": f"+9177{int(suffix[:8], 16) % 100000000:08d}",
            "college": "SYS College",
            "department": "Science",
            "designation": "Lecturer",
            "employment_status": "ACTIVE",
            **overrides,
        }
        response = client.post("/admin/faculty", headers=auth(self.admin.token), json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_authorization_inactive_and_expired_sessions(self):
        for path in ("/admin/master/students", "/admin/master/faculty", "/admin/operations/summary"):
            self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get(path, headers=auth(self.faculty.token)).status_code, 403)
            self.assertEqual(client.get(path, headers=auth(self.student.token)).status_code, 403)
            self.assertEqual(client.get(path, headers=auth(self.admin.token)).status_code, 200)
            self.assertEqual(client.get(path, headers=auth(self.super_token)).status_code, 200)

        stale_token = self._create_login_user("admin", f"P021-STALE-{uuid.uuid4().hex[:5]}")
        me = client.get("/auth/me", headers=auth(stale_token)).json()
        with database.SessionLocal() as db:
            row = db.query(models.User).filter(models.User.id == me["id"]).one()
            row.session_version += 1
            db.commit()
        self.assertEqual(client.get("/admin/master/students", headers=auth(stale_token)).status_code, 401)

        inactive_token = self._create_login_user("admin", f"P021-INACTIVE-{uuid.uuid4().hex[:5]}")
        me = client.get("/auth/me", headers=auth(inactive_token)).json()
        with database.SessionLocal() as db:
            row = db.query(models.User).filter(models.User.id == me["id"]).one()
            row.is_active = False
            db.commit()
        self.assertEqual(client.get("/admin/master/faculty", headers=auth(inactive_token)).status_code, 401)

    def test_searches_identifiers_name_email_and_mobile(self):
        student = self._student(name="Searchable Student", roll_number="ROLL-SEARCH-21", email="student.search21@example.com", mobile_number="+919876540021")
        faculty = self._faculty(name="Searchable Faculty", employee_code="EMP-SEARCH-21", email="faculty.search21@example.com", mobile_number="+919876540022")
        for term in ("ROLL-SEARCH-21", "Searchable Student", "student.search21", "540021"):
            body = client.get("/admin/master/students", headers=auth(self.admin.token), params={"search": term}).json()
            self.assertIn(student["id"], [item["id"] for item in body["items"]])
        for term in ("EMP-SEARCH-21", "Searchable Faculty", "faculty.search21", "540022"):
            body = client.get("/admin/master/faculty", headers=auth(self.admin.token), params={"search": term}).json()
            self.assertIn(faculty["id"], [item["id"] for item in body["items"]])

    def test_student_filters_combine_before_pagination(self):
        student = self._student(college="Filter College", admission_year=2025, present_year=2, academic_status="INACTIVE")
        course = client.post("/courses/", headers=auth(self.admin.token), json={"title": f"Filter Programme {uuid.uuid4().hex[:6]}"}).json()
        with database.SessionLocal() as db:
            db.add(models.StudentCourseEnrollment(student_id=student["id"], course_id=course["id"]))
            db.commit()
        params = {"college": "Filter College", "admission_year": 2025, "present_year": 2, "academic_status": "INACTIVE", "programme_id": course["id"], "page_size": 25}
        body = client.get("/admin/master/students", headers=auth(self.admin.token), params=params).json()
        self.assertEqual([item["id"] for item in body["items"]], [student["id"]])
        self.assertEqual(body["total"], 1)

    def test_faculty_filters_and_assignments(self):
        faculty = self._faculty(college="Faculty Filter College", department="Mathematics", designation="Professor", employment_status="ACTIVE")
        course = client.post("/courses/", headers=auth(self.admin.token), json={"title": f"Assignment Programme {uuid.uuid4().hex[:6]}"}).json()
        assignment = client.post("/admin/course-coordinators", headers=auth(self.admin.token), json={"faculty_id": faculty["id"], "course_id": course["id"]})
        self.assertEqual(assignment.status_code, 201, assignment.text)
        params = {"college": "Faculty Filter", "department": "Math", "designation": "Professor", "employment_status": "ACTIVE", "responsibility": "course_coordinator"}
        body = client.get("/admin/master/faculty", headers=auth(self.admin.token), params=params).json()
        self.assertIn(faculty["id"], [item["id"] for item in body["items"]])

    def test_every_sort_allowlist_both_directions_and_invalid_fields(self):
        self._student(name="AAA Sort Student", college="A College", admission_year=2024, present_year=1)
        self._student(name="ZZZ Sort Student", college="Z College", admission_year=2026, present_year=3)
        self._faculty(name="AAA Sort Faculty", department="A Department", designation="Assistant")
        self._faculty(name="ZZZ Sort Faculty", department="Z Department", designation="Professor")
        student_sorts = ("name", "roll_number", "email", "mobile", "college", "admission_year", "present_year", "registration_status", "academic_status", "created_at")
        faculty_sorts = ("name", "employee_code", "email", "mobile", "college", "department", "designation", "registration_status", "employment_status", "created_at")
        for path, fields in (("/admin/master/students", student_sorts), ("/admin/master/faculty", faculty_sorts)):
            for field in fields:
                for order in ("asc", "desc"):
                    response = client.get(path, headers=auth(self.admin.token), params={"sort": field, "order": order, "page_size": 25})
                    self.assertEqual(response.status_code, 200, (path, field, order, response.text))
            self.assertEqual(client.get(path, headers=auth(self.admin.token), params={"sort": "hashed_password"}).status_code, 422)
            self.assertEqual(client.get(path, headers=auth(self.admin.token), params={"private_field": "x"}).status_code, 422)

    def test_pagination_boundaries_totals_and_empty_results(self):
        prefix = f"Page-{uuid.uuid4().hex[:6]}"
        for index in range(27):
            self._student(name=f"{prefix}-{index:02d}")
        first = client.get("/admin/master/students", headers=auth(self.admin.token), params={"search": prefix, "sort": "name", "page": 1, "page_size": 25}).json()
        second = client.get("/admin/master/students", headers=auth(self.admin.token), params={"search": prefix, "sort": "name", "page": 2, "page_size": 25}).json()
        empty = client.get("/admin/master/students", headers=auth(self.admin.token), params={"search": prefix, "page": 3, "page_size": 25}).json()
        self.assertEqual(first["total"], 27)
        self.assertEqual(len(first["items"]), 25)
        self.assertEqual(len(second["items"]), 2)
        self.assertEqual(empty["items"], [])
        self.assertEqual(empty["total"], 27)

    def test_normalization_and_duplicate_contacts(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"normalize_{suffix}@example.com"
        mobile = f"+9188{int(suffix, 16) % 100000000:08d}"
        created = self._student(roll_number=f"  norm-{suffix}  ", email=f"  {email.upper()}  ", mobile_number=f" {mobile} ")
        self.assertEqual(created["roll_number"], f"NORM-{suffix.upper()}")
        duplicate_email = client.post("/admin/faculty", headers=auth(self.admin.token), json={"name": "Duplicate email", "employee_code": f"DUP-E-{suffix}", "email": email})
        duplicate_mobile = client.post("/admin/faculty", headers=auth(self.admin.token), json={"name": "Duplicate mobile", "employee_code": f"DUP-M-{suffix}", "mobile_number": mobile})
        self.assertEqual(duplicate_email.status_code, 409)
        self.assertEqual(duplicate_email.json()["detail"], "Email already exists")
        self.assertEqual(duplicate_mobile.status_code, 409)
        self.assertEqual(duplicate_mobile.json()["detail"], "Mobile number already exists")

    def test_update_bulk_partial_failures_assignment_and_audit(self):
        student = self._student(name="Before Update")
        update = client.put(f"/admin/students/{student['id']}", headers=auth(self.admin.token), json={"name": "After Update", "college": "Updated College"})
        self.assertEqual(update.status_code, 200, update.text)
        bulk = client.post("/admin/master/students/bulk-status", headers=auth(self.admin.token), json={"ids": [student["id"], 99999999], "action": "deactivate"})
        self.assertEqual(bulk.status_code, 200, bulk.text)
        self.assertEqual(bulk.json()["succeeded"], 1)
        self.assertEqual(bulk.json()["failed"], 1)

        faculty = self._faculty()
        course = client.post("/courses/", headers=auth(self.admin.token), json={"title": f"Bulk Course {uuid.uuid4().hex[:6]}"}).json()
        assigned = client.post("/admin/master/faculty/bulk-assignment", headers=auth(self.admin.token), json={"faculty_ids": [faculty["id"], 99999998], "assignment_type": "course_coordinator", "target_id": course["id"]})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        self.assertEqual((assigned.json()["succeeded"], assigned.json()["failed"]), (1, 1))
        self.assertEqual(client.delete(f"/admin/students/{student['id']}", headers=auth(self.admin.token)).status_code, 405)

        self.assertEqual(client.get("/admin/audit-logs", headers=auth(self.admin.token)).status_code, 403)
        audit_rows = client.get("/admin/audit-logs", headers=auth(self.super_token))
        self.assertEqual(audit_rows.status_code, 200, audit_rows.text)
        actions = {row["action"] for row in audit_rows.json()}
        self.assertIn("student.update", actions)
        self.assertIn("student.deactivate", actions)
        self.assertIn("faculty.assign_course_coordinator", actions)

    def test_export_is_filtered_authorized_and_formula_safe(self):
        marker = f"Export-{uuid.uuid4().hex[:6]}"
        self._student(name=f"={marker}", college=marker)
        response = client.get("/admin/master/students/export", headers=auth(self.admin.token), params={"search": marker})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("SYS_student_master_", response.headers["content-disposition"])
        self.assertIn(f"'={marker}", response.text)
        self.assertNotIn("hashed_password", response.text)
        self.assertEqual(client.get("/admin/master/students/export", headers=auth(self.student.token)).status_code, 403)

    def test_summary_uses_real_data_and_no_fake_activity(self):
        summary = client.get("/admin/operations/summary", headers=auth(self.admin.token))
        self.assertEqual(summary.status_code, 200, summary.text)
        body = summary.json()
        self.assertGreaterEqual(body["students"]["total"], 1)
        self.assertIn("pending_activation", body["students"])
        self.assertIn("active", body["programmes"])
        self.assertFalse(body["recent_admin_activity"]["available"])
        self.assertEqual(body["recent_admin_activity"]["items"], [])
        super_summary = client.get("/admin/operations/summary", headers=auth(self.super_token)).json()
        self.assertTrue(super_summary["recent_admin_activity"]["available"])


if __name__ == "__main__":
    unittest.main()
