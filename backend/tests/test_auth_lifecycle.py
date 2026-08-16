"""P0-020 controlled activation, unified login, OTP recovery, and session tests."""

from __future__ import annotations

import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from tests import isolation as _test_isolation  # noqa: F401
from fastapi.testclient import TestClient

from app import database, models
from app.main import app
from app.services import authentication as auth_service
from app.services.otp_delivery import DeliveryResult, get_otp_provider
from tests.auth_helpers import ProtectedUserFactory


class OutboxOtpProvider:
    def __init__(self):
        self.otps: list[dict] = []
        self.notices: list[dict] = []

    def send_otp(self, *, channel, destination, code, purpose):
        self.otps.append(
            {
                "channel": channel,
                "destination": destination,
                "code": code,
                "purpose": purpose,
            }
        )
        return DeliveryResult(True)

    def send_security_notice(self, *, channel, destination, subject, message):
        self.notices.append(
            {
                "channel": channel,
                "destination": destination,
                "subject": subject,
                "message": message,
            }
        )
        return DeliveryResult(True)

    def code_for(self, destination: str, purpose: str) -> str:
        return next(
            row["code"]
            for row in reversed(self.otps)
            if row["destination"] == destination and row["purpose"] == purpose
        )


class AuthenticationLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.outbox = OutboxOtpProvider()
        app.dependency_overrides[get_otp_provider] = lambda: cls.outbox
        cls.users = ProtectedUserFactory(cls.client, "P020")
        cls.admin = cls.users.create("admin")

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_otp_provider, None)
        cls.client.close()

    def setUp(self):
        self.outbox.otps.clear()
        self.outbox.notices.clear()
        with database.SessionLocal() as db:
            db.query(models.AuthChallenge).delete()
            db.commit()

    @staticmethod
    def _email(prefix: str) -> str:
        return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"

    @staticmethod
    def _mobile() -> str:
        return f"+91{secrets_digits(10)}"

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _create_master(
        self,
        role: str,
        *,
        institutional_id: str | None = None,
        email: str | None = None,
        mobile: str | None = None,
    ) -> dict:
        institutional_id = institutional_id or f"P020-{uuid.uuid4().hex[:10]}"
        payload = {
            "name": f"Pending {role}",
            "email": email,
            "mobile_number": mobile,
            "mobile_is_personal": True,
            "roll_number" if role == "student" else "employee_code": institutional_id,
        }
        response = self.client.post(
            f"/admin/{'students' if role == 'student' else 'faculty'}",
            headers=self._auth(self.admin.token),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["account_status"], "PENDING_ACTIVATION")
        self.assertIsNone(body["email"])
        return body

    def _verify_ownership(self, *, role: str, institutional_id: str, destination: str, channel="email"):
        started = self.client.post(
            "/auth/activation/start",
            json={"role": role, "institutional_id": institutional_id, "channel": channel},
        )
        self.assertEqual(started.status_code, 200, started.text)
        code = self.outbox.code_for(destination, auth_service.PURPOSE_ACTIVATION_OWNERSHIP)
        verified = self.client.post(
            "/auth/activation/verify-otp",
            json={"challenge_id": started.json()["challenge_id"], "code": code},
        )
        self.assertEqual(verified.status_code, 200, verified.text)
        return verified.json()["authorization"]

    def _verify_contact(self, ownership: str, contact_type: str, value: str):
        sent = self.client.post(
            "/auth/activation/verify-contact",
            json={
                "action": "send",
                "ownership_authorization": ownership,
                "contact_type": contact_type,
                "contact_value": value,
            },
        )
        self.assertEqual(sent.status_code, 200, sent.text)
        purpose = (
            auth_service.PURPOSE_ACTIVATION_EMAIL
            if contact_type == "email"
            else auth_service.PURPOSE_ACTIVATION_MOBILE
        )
        code = self.outbox.code_for(value, purpose)
        verified = self.client.post(
            "/auth/activation/verify-contact",
            json={
                "action": "verify",
                "ownership_authorization": ownership,
                "contact_type": contact_type,
                "challenge_id": sent.json()["challenge_id"],
                "code": code,
            },
        )
        self.assertEqual(verified.status_code, 200, verified.text)
        return verified.json()["authorization"]

    def _activation_payload(self, role: str = "student"):
        institutional_id = f"P020-{role[:1].upper()}-{uuid.uuid4().hex[:8]}"
        preloaded_email = self._email("institutional")
        self._create_master(
            role,
            institutional_id=institutional_id,
            email=preloaded_email,
            mobile=self._mobile(),
        )
        ownership = self._verify_ownership(
            role=role,
            institutional_id=institutional_id,
            destination=preloaded_email,
        )
        email = self._email("personal")
        mobile = self._mobile()
        return {
            "institutional_id": institutional_id,
            "ownership_authorization": ownership,
            "email": email,
            "email_authorization": self._verify_contact(ownership, "email", email),
            "mobile_number": mobile,
            "mobile_authorization": self._verify_contact(ownership, "mobile", mobile),
            "password": "ActivatedPass123!",
            "confirm_password": "ActivatedPass123!",
        }

    def _complete_activation(self, role: str = "student") -> tuple[dict, dict]:
        payload = self._activation_payload(role)
        completed = self.client.post("/auth/activation/complete", json=self._complete_body(payload))
        self.assertEqual(completed.status_code, 200, completed.text)
        return payload, completed.json()

    @staticmethod
    def _complete_body(payload: dict) -> dict:
        return {key: value for key, value in payload.items() if key != "institutional_id"}

    def _start_reset(self, identifier: str, channel: str, destination: str):
        response = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": identifier, "channel": channel},
        )
        self.assertEqual(response.status_code, 200, response.text)
        purpose = (
            auth_service.PURPOSE_PASSWORD_RESET_EMAIL
            if channel == "email"
            else auth_service.PURPOSE_PASSWORD_RESET_MOBILE
        )
        code = self.outbox.code_for(destination, purpose)
        verified = self.client.post(
            "/auth/password-reset/verify-otp",
            json={"challenge_id": response.json()["challenge_id"], "code": code},
        )
        self.assertEqual(verified.status_code, 200, verified.text)
        return verified.json()["authorization"]

    def test_valid_student_and_faculty_activation_derives_role(self):
        for role in ("student", "faculty"):
            payload, _ = self._complete_activation(role)
            login = self.client.post(
                "/auth/login",
                data={"username": payload["email"], "password": payload["password"]},
            )
            self.assertEqual(login.status_code, 200, login.text)
            me = self.client.get("/auth/me", headers=self._auth(login.json()["access_token"]))
            self.assertEqual(me.json()["role"], role)

    def test_unknown_inactive_claimed_and_role_tampering_are_non_enumerating(self):
        roll = f"P020-X-{uuid.uuid4().hex[:8]}"
        contact = self._email("inactive")
        inactive = self._create_master("student", institutional_id=roll, email=contact)
        self.client.post(
            f"/admin/students/{inactive['id']}/deactivate",
            headers=self._auth(self.admin.token),
        )

        claimed = self.users.create("student", {"roll_number": f"P020-C-{uuid.uuid4().hex[:8]}"})
        cases = [
            {"role": "student", "institutional_id": "UNKNOWN-P020", "channel": "email"},
            {"role": "student", "institutional_id": roll, "channel": "email"},
            {"role": "student", "institutional_id": claimed.user.roll_number, "channel": "email"},
            {"role": "faculty", "institutional_id": roll, "channel": "email"},
        ]
        for payload in cases:
            response = self.client.post("/auth/activation/start", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["message"], auth_service.GENERIC_ACTIVATION_ERROR)
            self.assertEqual(set(response.json()), {"challenge_id", "message"})
        self.assertEqual(self.outbox.otps, [])

    def test_contact_mismatch_unverified_contact_and_duplicates_are_rejected(self):
        payload = self._activation_payload("student")
        mismatch = {**self._complete_body(payload), "email": self._email("different")}
        response = self.client.post("/auth/activation/complete", json=mismatch)
        self.assertEqual(response.status_code, 400)

        unverified = {
            **self._complete_body(payload),
            "mobile_authorization": "not-a-valid-authorization-token",
        }
        response = self.client.post("/auth/activation/complete", json=unverified)
        self.assertEqual(response.status_code, 400)

        existing = self.users.create(
            "faculty",
            {
                "employee_code": f"P020-D-{uuid.uuid4().hex[:8]}",
                "mobile_number": self._mobile(),
            },
        )
        ownership = payload["ownership_authorization"]
        duplicate_email = self.client.post(
            "/auth/activation/verify-contact",
            json={
                "action": "send",
                "ownership_authorization": ownership,
                "contact_type": "email",
                "contact_value": existing.user.email,
            },
        )
        duplicate_mobile = self.client.post(
            "/auth/activation/verify-contact",
            json={
                "action": "send",
                "ownership_authorization": ownership,
                "contact_type": "mobile",
                "contact_value": existing.user.mobile_number,
            },
        )
        self.assertEqual(duplicate_email.status_code, 409)
        self.assertEqual(duplicate_mobile.status_code, 409)

    def test_atomic_activation_claim_allows_only_one_completion(self):
        payload = self._activation_payload("student")
        complete_payload = self._complete_body(payload)

        def complete():
            return self.client.post("/auth/activation/complete", json=complete_payload).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = sorted(executor.map(lambda _: complete(), range(2)))
        self.assertEqual(statuses, [200, 409])

    def test_login_by_email_mobile_roll_number_and_employee_code(self):
        student = self.users.create(
            "student",
            {"roll_number": f"P020-LS-{uuid.uuid4().hex[:7]}", "mobile_number": self._mobile()},
        )
        faculty = self.users.create(
            "faculty",
            {"employee_code": f"P020-LF-{uuid.uuid4().hex[:7]}", "mobile_number": self._mobile()},
        )
        for identifier, identity in (
            (student.user.email.upper(), student),
            (student.user.mobile_number, student),
            (student.user.roll_number.lower(), student),
            (faculty.user.employee_code.lower(), faculty),
        ):
            login = self.client.post(
                "/auth/login",
                data={"username": identifier, "password": "TestPass123!"},
            )
            self.assertEqual(login.status_code, 200, login.text)

    def test_invalid_and_ambiguous_identifiers_use_generic_error(self):
        collision = self._email("collision")
        self.users.create("student", {"roll_number": f"P020-A-{uuid.uuid4().hex[:7]}"})
        first = self.users.create("student", {"roll_number": f"P020-B-{uuid.uuid4().hex[:7]}"})
        with database.SessionLocal() as db:
            one = db.query(models.User).filter(models.User.id == first.user_id).one()
            one.email = collision
            one.institutional_email = collision
            one.email_verified = True
            db.add(
                models.User(
                    name="Ambiguous faculty",
                    email=self._email("other"),
                    institutional_email=self._email("institutional"),
                    email_verified=True,
                    hashed_password=one.hashed_password,
                    role="faculty",
                    employee_code=collision.upper(),
                    is_active=True,
                    account_status="ACTIVE",
                    session_version=1,
                )
            )
            db.commit()

        for identifier in ("does-not-exist", collision):
            response = self.client.post(
                "/auth/login",
                data={"username": identifier, "password": "TestPass123!"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], auth_service.GENERIC_LOGIN_ERROR)

    def test_password_reset_by_email_invalidates_password_and_existing_jwt(self):
        user = self.users.create(
            "student",
            {"roll_number": f"P020-R-{uuid.uuid4().hex[:8]}", "mobile_number": self._mobile()},
        )
        old_login = self.client.post(
            "/auth/login",
            data={"username": user.user.email, "password": "TestPass123!"},
        ).json()
        authorization = self._start_reset(user.user.email, "email", user.user.email)
        reset = self.client.post(
            "/auth/password-reset/complete",
            json={
                "reset_authorization": authorization,
                "password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!",
            },
        )
        self.assertEqual(reset.status_code, 200, reset.text)
        self.assertEqual(
            self.client.get("/auth/me", headers=self._auth(old_login["access_token"])).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": user.user.email, "password": "TestPass123!"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": user.user.email, "password": "NewSecurePass123!"},
            ).status_code,
            200,
        )
        self.assertTrue(self.outbox.notices)
        self.assertNotIn("NewSecurePass123!", str(self.outbox.notices))

    def test_password_reset_by_mobile_and_authorization_is_single_use(self):
        mobile = self._mobile()
        user = self.users.create(
            "faculty",
            {"employee_code": f"P020-RM-{uuid.uuid4().hex[:7]}", "mobile_number": mobile},
        )
        authorization = self._start_reset(mobile, "mobile", mobile)
        payload = {
            "reset_authorization": authorization,
            "password": "MobileResetPass123!",
            "confirm_password": "MobileResetPass123!",
        }
        self.assertEqual(self.client.post("/auth/password-reset/complete", json=payload).status_code, 200)
        self.assertEqual(self.client.post("/auth/password-reset/complete", json=payload).status_code, 400)
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": user.user.employee_code, "password": "MobileResetPass123!"},
            ).status_code,
            200,
        )

    def test_password_reset_does_not_enumerate_accounts(self):
        known = self.users.create("student", {"roll_number": f"P020-N-{uuid.uuid4().hex[:8]}"})
        known_response = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": known.user.email, "channel": "email"},
        )
        unknown_response = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": self._email("unknown"), "channel": "email"},
        )
        self.assertEqual(known_response.status_code, unknown_response.status_code)
        self.assertEqual(known_response.json()["message"], unknown_response.json()["message"])
        self.assertEqual(set(known_response.json()), set(unknown_response.json()))

    def test_otp_expiration_reuse_attempt_limit_and_superseding(self):
        user = self.users.create("student", {"roll_number": f"P020-O-{uuid.uuid4().hex[:8]}"})
        start = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        challenge_id = start.json()["challenge_id"]
        code = self.outbox.code_for(user.user.email, auth_service.PURPOSE_PASSWORD_RESET_EMAIL)
        with database.SessionLocal() as db:
            challenge = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == challenge_id).one()
            challenge.expires_at = auth_service.utcnow() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(
            self.client.post(
                "/auth/password-reset/verify-otp",
                json={"challenge_id": challenge_id, "code": code},
            ).status_code,
            400,
        )

        self.setUp()
        start = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        challenge_id = start.json()["challenge_id"]
        code = self.outbox.code_for(user.user.email, auth_service.PURPOSE_PASSWORD_RESET_EMAIL)
        for _ in range(5):
            self.client.post(
                "/auth/password-reset/verify-otp",
                json={"challenge_id": challenge_id, "code": "000000" if code != "000000" else "999999"},
            )
        self.assertEqual(
            self.client.post(
                "/auth/password-reset/verify-otp",
                json={"challenge_id": challenge_id, "code": code},
            ).status_code,
            400,
        )

        self.setUp()
        first = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        with database.SessionLocal() as db:
            row = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == first.json()["challenge_id"]).one()
            row.failed_attempts = 2
            row.resend_available_at = auth_service.utcnow() - timedelta(seconds=1)
            db.commit()
        second = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        self.assertNotEqual(first.json()["challenge_id"], second.json()["challenge_id"])
        with database.SessionLocal() as db:
            old = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == first.json()["challenge_id"]).one()
            new = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == second.json()["challenge_id"]).one()
            self.assertEqual(old.status, "SUPERSEDED")
            self.assertEqual(new.failed_attempts, 2)

        new_code = self.outbox.code_for(user.user.email, auth_service.PURPOSE_PASSWORD_RESET_EMAIL)
        verified = self.client.post(
            "/auth/password-reset/verify-otp",
            json={"challenge_id": second.json()["challenge_id"], "code": new_code},
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/auth/password-reset/verify-otp",
                json={"challenge_id": second.json()["challenge_id"], "code": new_code},
            ).status_code,
            400,
        )

    def test_resend_cooldown_and_limit(self):
        user = self.users.create("student", {"roll_number": f"P020-RL-{uuid.uuid4().hex[:7]}"})
        first = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        cooldown = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.roll_number, "channel": "email"},
        )
        self.assertEqual(first.json()["challenge_id"], cooldown.json()["challenge_id"])
        self.assertEqual(len(self.outbox.otps), 1)

        latest_id = first.json()["challenge_id"]
        for _ in range(auth_service.MAX_SENDS_PER_SUBJECT):
            with database.SessionLocal() as db:
                row = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == latest_id).one()
                row.resend_available_at = auth_service.utcnow() - timedelta(seconds=1)
                db.commit()
            response = self.client.post(
                "/auth/password-reset/start",
                json={"identifier": user.user.email, "channel": "email"},
            )
            latest_id = response.json()["challenge_id"]
        with database.SessionLocal() as db:
            latest = db.query(models.AuthChallenge).filter(models.AuthChallenge.id == latest_id).one()
            self.assertEqual(latest.status, "LOCKED")
            self.assertGreater(latest.send_count, auth_service.MAX_SENDS_PER_SUBJECT)

    def test_disabled_account_cannot_reset_or_use_existing_token(self):
        user = self.users.create("student", {"roll_number": f"P020-DIS-{uuid.uuid4().hex[:6]}"})
        login = self.client.post(
            "/auth/login",
            data={"username": user.user.email, "password": "TestPass123!"},
        ).json()
        disabled = self.client.post(
            f"/admin/users/{user.user_id}/disable",
            headers=self._auth(self.admin.token),
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.json()["account_status"], "DISABLED")
        self.assertEqual(self.client.get("/auth/me", headers=self._auth(login["access_token"])).status_code, 401)
        before = len(self.outbox.otps)
        response = self.client.post(
            "/auth/password-reset/start",
            json={"identifier": user.user.email, "channel": "email"},
        )
        self.assertEqual(response.json()["message"], auth_service.GENERIC_RECOVERY_MESSAGE)
        self.assertEqual(len(self.outbox.otps), before)

    def test_validation_responses_do_not_echo_passwords_or_otps(self):
        secret = "tiny-secret"
        response = self.client.post(
            "/auth/password-reset/complete",
            json={
                "reset_authorization": "invalid-reset-authorization-token",
                "password": secret,
                "confirm_password": secret,
            },
        )
        self.assertNotIn(secret, response.text)
        wrong_otp = "123456"
        response = self.client.post(
            "/auth/password-reset/verify-otp",
            json={"challenge_id": "x" * 32, "code": wrong_otp},
        )
        self.assertNotIn(wrong_otp, response.text)


def secrets_digits(length: int) -> str:
    value = uuid.uuid4().int % (10**length)
    return f"{value:0{length}d}"


if __name__ == "__main__":
    unittest.main()
