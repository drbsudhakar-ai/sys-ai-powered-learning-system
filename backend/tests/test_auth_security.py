"""Focused authentication and account-provisioning security tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import isolation as _test_isolation  # noqa: E402,F401
from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import academic_auth, database, models, roles, utils  # noqa: E402
from app.routes import admin, auth  # noqa: E402


class AuthenticationSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        models.User.__table__.create(bind=cls.engine)

        test_app = FastAPI()
        test_app.include_router(auth.router)
        test_app.include_router(admin.router)

        @test_app.get("/_test/admin-only")
        def admin_only(user: models.User = Depends(auth.require_roles("admin"))):
            return {"role": user.role}

        @test_app.get("/_test/super-admin-only")
        def super_admin_only(user: models.User = Depends(auth.require_super_admin)):
            return {"role": user.role}

        def override_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        test_app.dependency_overrides[database.get_db] = override_db
        cls.client = TestClient(test_app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.engine.dispose()

    def _email(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}@example.com"

    def _create_user(self, role: str, *, active: bool = True) -> tuple[models.User, str]:
        password = "TestPass123!"
        user = models.User(
            name=f"Auth {role}",
            email=self._email(role),
            hashed_password=utils.hash_password(password),
            role=role,
            roll_number=f"ROLL-{uuid.uuid4().hex[:8]}".upper() if role == "student" else None,
            employee_code=(
                f"EMP-{uuid.uuid4().hex[:8]}".upper()
                if role in {"faculty", "admin"}
                else None
            ),
            is_active=active,
        )
        with self.session_factory() as db:
            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)
        return user, password

    def _login(self, user: models.User, password: str) -> str:
        response = self.client.post(
            "/auth/login",
            data={"username": user.email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _registration_payload(self, role: str, email: str | None = None) -> dict:
        payload = {
            "name": f"Provisioned {role}",
            "email": email or self._email(f"provisioned-{role}"),
            "role": role,
            "password": "ProvisionedPass123!",
        }
        if role == "student":
            payload["roll_number"] = f"ROLL-{uuid.uuid4().hex[:8]}"
        elif role == "faculty":
            payload["employee_code"] = f"EMP-{uuid.uuid4().hex[:8]}"
        return payload

    def test_unauthenticated_registration_cannot_create_account(self):
        email = self._email("public-registration")
        response = self.client.post(
            "/auth/register",
            json=self._registration_payload("student", email),
        )
        self.assertEqual(response.status_code, 401)
        with self.session_factory() as db:
            self.assertIsNone(db.query(models.User).filter(models.User.email == email).first())

    def test_authenticated_non_admin_registration_is_denied(self):
        student, password = self._create_user("student")
        token = self._login(student, password)
        response = self.client.post(
            "/auth/register",
            headers=self._auth(token),
            json=self._registration_payload("faculty"),
        )
        self.assertEqual(response.status_code, 403)

    def test_administrator_roles_cannot_be_provisioned(self):
        admin, password = self._create_user("admin")
        token = self._login(admin, password)
        for forbidden_role in (roles.ADMIN, roles.SUPER_ADMIN):
            with self.subTest(role=forbidden_role):
                email = self._email(f"forbidden-{forbidden_role}")
                payload = self._registration_payload("faculty", email)
                payload["role"] = forbidden_role
                for path in ("/auth/register", "/admin/users/provision"):
                    response = self.client.post(
                        path,
                        headers=self._auth(token),
                        json=payload,
                    )
                    self.assertEqual(response.status_code, 422, response.text)
                with self.session_factory() as db:
                    self.assertIsNone(
                        db.query(models.User).filter(models.User.email == email).first()
                    )

    def test_activation_rejects_administrator_roles(self):
        for forbidden_role in (roles.ADMIN, roles.SUPER_ADMIN):
            response = self.client.post(
                "/auth/activation/start",
                json={
                    "role": forbidden_role,
                    "institutional_id": "SYS-ADMIN",
                    "channel": "email",
                },
            )
            self.assertEqual(response.status_code, 422, response.text)

    def test_super_admin_inherits_admin_permissions_and_me_role(self):
        super_admin, password = self._create_user(roles.SUPER_ADMIN)
        token = self._login(super_admin, password)
        self.assertTrue(academic_auth.is_admin(super_admin))

        for path in ("/_test/admin-only", "/_test/super-admin-only", "/admin/students"):
            response = self.client.get(path, headers=self._auth(token))
            self.assertEqual(response.status_code, 200, response.text)

        me = self.client.get("/auth/me", headers=self._auth(token))
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["role"], roles.SUPER_ADMIN)

    def test_ordinary_admin_cannot_use_super_admin_dependency(self):
        admin_user, password = self._create_user(roles.ADMIN)
        token = self._login(admin_user, password)
        self.assertEqual(
            self.client.get("/_test/admin-only", headers=self._auth(token)).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/_test/super-admin-only", headers=self._auth(token)).status_code,
            403,
        )

    def test_faculty_and_student_cannot_use_admin_dependencies(self):
        for role in (roles.FACULTY, roles.STUDENT):
            user, password = self._create_user(role)
            token = self._login(user, password)
            for path in ("/_test/admin-only", "/_test/super-admin-only", "/admin/students"):
                response = self.client.get(path, headers=self._auth(token))
                self.assertEqual(response.status_code, 403, (role, path, response.text))

    def test_inactive_super_admin_is_rejected(self):
        super_admin, password = self._create_user(roles.SUPER_ADMIN)
        token = self._login(super_admin, password)
        with self.session_factory() as db:
            stored = db.query(models.User).filter(models.User.id == super_admin.id).one()
            stored.is_active = False
            db.commit()

        for path in ("/auth/me", "/_test/admin-only", "/_test/super-admin-only"):
            response = self.client.get(path, headers=self._auth(token))
            self.assertEqual(response.status_code, 401, (path, response.text))

    def test_admin_can_provision_student_and_faculty(self):
        admin, password = self._create_user("admin")
        token = self._login(admin, password)

        for role in ("student", "faculty"):
            response = self.client.post(
                "/auth/register",
                headers=self._auth(token),
                json=self._registration_payload(role),
            )
            self.assertEqual(response.status_code, 201, response.text)
            body = response.json()
            self.assertEqual(body["role"], role)
            self.assertNotIn("password", body)
            self.assertNotIn("hashed_password", body)

    def test_weak_password_is_rejected_without_echoing_it(self):
        admin, password = self._create_user("admin")
        token = self._login(admin, password)
        payload = self._registration_payload("student")
        payload["password"] = "short"
        response = self.client.post(
            "/auth/register",
            headers=self._auth(token),
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("short", response.text)

    def test_missing_identifier_does_not_echo_password(self):
        admin, password = self._create_user("admin")
        token = self._login(admin, password)
        payload = self._registration_payload("student")
        submitted_password = payload["password"]
        payload.pop("roll_number")
        response = self.client.post(
            "/auth/register",
            headers=self._auth(token),
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(submitted_password, response.text)

    def test_token_issued_before_deactivation_is_rejected(self):
        user, password = self._create_user("admin")
        token = self._login(user, password)

        with self.session_factory() as db:
            stored = db.query(models.User).filter(models.User.id == user.id).one()
            stored.is_active = False
            db.commit()

        response = self.client.get("/auth/me", headers=self._auth(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid or expired token"})

        provision = self.client.post(
            "/auth/register",
            headers=self._auth(token),
            json=self._registration_payload("student"),
        )
        self.assertEqual(provision.status_code, 401)

    def test_active_token_behavior_still_succeeds(self):
        user, password = self._create_user("faculty")
        token = self._login(user, password)
        response = self.client.get("/auth/me", headers=self._auth(token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], user.id)
        self.assertTrue(response.json()["is_active"])


if __name__ == "__main__":
    unittest.main()
