"""Focused authentication and account-provisioning security tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import isolation as _test_isolation  # noqa: E402,F401
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database, models, utils  # noqa: E402
from app.routes import auth  # noqa: E402


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
            roll_number=f"ROLL-{uuid.uuid4().hex[:8]}" if role == "student" else None,
            employee_code=f"EMP-{uuid.uuid4().hex[:8]}" if role in {"faculty", "admin"} else None,
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

    def test_admin_cannot_provision_another_admin(self):
        admin, password = self._create_user("admin")
        token = self._login(admin, password)
        email = self._email("forbidden-admin")
        payload = self._registration_payload("faculty", email)
        payload["role"] = "admin"
        response = self.client.post(
            "/auth/register",
            headers=self._auth(token),
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        with self.session_factory() as db:
            self.assertIsNone(db.query(models.User).filter(models.User.email == email).first())

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
