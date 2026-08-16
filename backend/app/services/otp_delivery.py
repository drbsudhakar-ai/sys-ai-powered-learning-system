"""OTP and security-notice delivery interfaces.

The production default sends email only when SMTP is configured. SMS remains an
explicit provider boundary and fails closed until an implementation is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.notifications import send_email


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    failure_reason: str | None = None


class OtpDeliveryProvider(Protocol):
    def send_otp(
        self,
        *,
        channel: str,
        destination: str,
        code: str,
        purpose: str,
    ) -> DeliveryResult: ...

    def send_security_notice(
        self,
        *,
        channel: str,
        destination: str,
        subject: str,
        message: str,
    ) -> DeliveryResult: ...


class SystemOtpDeliveryProvider:
    """Production provider using configured SMTP and no development OTP output."""

    def send_otp(
        self,
        *,
        channel: str,
        destination: str,
        code: str,
        purpose: str,
    ) -> DeliveryResult:
        if channel != "email":
            return DeliveryResult(False, "SMS provider is not configured")
        try:
            send_email(
                [destination],
                "Your SYS verification code",
                (
                    f"Your SYS verification code is {code}. "
                    "It expires in 10 minutes. If you did not request this, ignore this message."
                ),
            )
            return DeliveryResult(True)
        except Exception:
            return DeliveryResult(False, "Email provider is not configured or delivery failed")

    def send_security_notice(
        self,
        *,
        channel: str,
        destination: str,
        subject: str,
        message: str,
    ) -> DeliveryResult:
        if channel != "email":
            return DeliveryResult(False, "SMS provider is not configured")
        try:
            send_email([destination], subject, message)
            return DeliveryResult(True)
        except Exception:
            return DeliveryResult(False, "Email provider is not configured or delivery failed")


def get_otp_provider() -> OtpDeliveryProvider:
    return SystemOtpDeliveryProvider()
