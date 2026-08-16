"""Authentication helpers for protected user-provisioning integration tests."""

from __future__ import annotations

import atexit
import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient

from app import database, models, utils
from tests.isolation import configure_test_app


_TEST_PASSWORD = "TestPass123!"


@dataclass(frozen=True)
class TestIdentity:
    token: str
    user_id: int
    user: models.User


class ProtectedUserFactory:
    """Bootstrap one test admin and provision all other users as that admin."""

    def __init__(self, client: TestClient, prefix: str):
        self.client = client
        self.prefix = prefix
        self._admin: TestIdentity | None = None
        configure_test_app(self.client.app)
        atexit.register(self.client.close)

    def create(self, role: str, extra: dict | None = None) -> TestIdentity:
        if self._admin is None:
            self._admin = self._bootstrap_admin()

        if role == "admin":
            return self._admin
        if role not in {"student", "faculty"}:
            raise AssertionError(f"Unsupported test role: {role}")

        email = self._email(role)
        payload = {
            "name": f"{self.prefix} {role}",
            "email": email,
            "role": role,
            "password": _TEST_PASSWORD,
            **(extra or {}),
        }
        response = self.client.post(
            "/admin/users/provision",
            headers=self._authorization(self._admin.token),
            json=payload,
        )
        assert response.status_code == 201, response.text
        return self._login(email, response.json()["id"])

    def _bootstrap_admin(self) -> TestIdentity:
        email = self._email("admin")
        db = database.SessionLocal()
        try:
            admin = models.User(
                name=f"{self.prefix} admin",
                email=email,
                institutional_email=email,
                email_verified=True,
                hashed_password=utils.hash_password(_TEST_PASSWORD),
                role="admin",
                employee_code=f"{self.prefix}-{uuid.uuid4().hex[:10]}",
                is_active=True,
                account_status="ACTIVE",
                session_version=1,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_id = admin.id
        finally:
            db.close()

        return self._login(email, admin_id)

    def _login(self, email: str, user_id: int) -> TestIdentity:
        response = self.client.post(
            "/auth/login",
            data={"username": email, "password": _TEST_PASSWORD},
        )
        assert response.status_code == 200, response.text

        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            assert user is not None
            db.expunge(user)
        finally:
            db.close()

        return TestIdentity(
            token=response.json()["access_token"],
            user_id=user_id,
            user=user,
        )

    @staticmethod
    def _authorization(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _email(self, role: str) -> str:
        return f"{self.prefix.lower()}_{role}_{uuid.uuid4().hex[:10]}@example.com"
