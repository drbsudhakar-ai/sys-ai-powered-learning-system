"""Controlled activation, unified identifiers, OTP recovery, and session security."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, roles, utils
from app.config import settings
from app.services.otp_delivery import OtpDeliveryProvider


ACCOUNT_PENDING = "PENDING_ACTIVATION"
ACCOUNT_ACTIVE = "ACTIVE"
ACCOUNT_DISABLED = "DISABLED"
ACCOUNT_STATES = {ACCOUNT_PENDING, ACCOUNT_ACTIVE, ACCOUNT_DISABLED}

PURPOSE_ACTIVATION_OWNERSHIP = "ACTIVATION_OWNERSHIP"
PURPOSE_ACTIVATION_EMAIL = "ACTIVATION_EMAIL"
PURPOSE_ACTIVATION_MOBILE = "ACTIVATION_MOBILE"
PURPOSE_PASSWORD_RESET_EMAIL = "PASSWORD_RESET_EMAIL"
PURPOSE_PASSWORD_RESET_MOBILE = "PASSWORD_RESET_MOBILE"

OTP_LIFETIME = timedelta(minutes=10)
AUTHORIZATION_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
RATE_WINDOW = timedelta(hours=1)
MAX_FAILED_ATTEMPTS = 5
MAX_SENDS_PER_SUBJECT = 5
MAX_SENDS_PER_IP = 30

GENERIC_LOGIN_ERROR = "The login identifier or password is incorrect."
GENERIC_ACTIVATION_ERROR = (
    "We couldn’t verify this institutional ID for registration. "
    "Check the details or contact your SYS administrator."
)
GENERIC_RECOVERY_MESSAGE = (
    "If the details match an active SYS account, a verification code has been sent."
)
GENERIC_OTP_ERROR = "The verification code is invalid or expired."


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_email(value: str) -> str:
    normalized = (value or "").strip().lower()
    if len(normalized) > 255 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise ValueError("Invalid email address")
    return normalized


def normalize_mobile(value: str) -> str:
    normalized = re.sub(r"[\s().-]", "", (value or "").strip())
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        raise ValueError("Mobile number must use E.164 format")
    return normalized


def normalize_institutional_id(value: str) -> str:
    normalized = (value or "").strip().upper()
    if not normalized or len(normalized) > 50:
        raise ValueError("Invalid institutional identifier")
    return normalized


def normalized_identifier_expression(column):
    """Database expression matching the institutional-ID storage contract."""

    return func.upper(func.trim(column))


def _secret_hash(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _otp_hash(challenge_id: str, code: str) -> str:
    return _secret_hash(f"otp:{challenge_id}:{code}")


def _authorization_hash(value: str) -> str:
    return _secret_hash(f"authorization:{value}")


def _request_ip_hash(request_ip: str | None) -> str:
    return _secret_hash(f"ip:{request_ip or 'unknown'}")


def _contact_hash(value: str) -> str:
    return _secret_hash(f"contact:{value}")


def account_can_authenticate(user: models.User | None) -> bool:
    return bool(
        user
        and user.is_active is True
        and user.account_status == ACCOUNT_ACTIVE
        and utils.is_usable_password_hash(user.hashed_password)
    )


def find_users_by_identifier(db: Session, identifier: str) -> list[models.User]:
    raw = (identifier or "").strip()
    if not raw:
        return []

    conditions = []
    try:
        email = normalize_email(raw)
        conditions.append(
            and_(models.User.email_verified.is_(True), func.lower(models.User.email) == email)
        )
    except ValueError:
        pass

    try:
        mobile = normalize_mobile(raw)
        conditions.append(
            and_(
                models.User.mobile_verified.is_(True),
                models.User.mobile_is_personal.is_(True),
                models.User.mobile_number == mobile,
            )
        )
    except ValueError:
        pass

    try:
        institutional_id = normalize_institutional_id(raw)
        conditions.extend(
            [
                normalized_identifier_expression(models.User.roll_number) == institutional_id,
                normalized_identifier_expression(models.User.employee_code) == institutional_id,
            ]
        )
    except ValueError:
        pass

    if not conditions:
        return []
    rows = db.query(models.User).filter(or_(*conditions)).all()
    return list({row.id: row for row in rows}.values())


def authenticate_identifier(db: Session, identifier: str, password: str) -> models.User | None:
    matches = find_users_by_identifier(db, identifier)
    if len(matches) != 1:
        return None
    user = matches[0]
    if not account_can_authenticate(user):
        return None
    if not utils.verify_password(password, user.hashed_password):
        return None
    return user


def provision_active_user(
    db: Session,
    *,
    name: str,
    email: str,
    role: str,
    password: str,
    roll_number: str | None = None,
    employee_code: str | None = None,
    mobile_number: str | None = None,
) -> models.User:
    role = roles.normalize_role(role)
    if role not in roles.PROVISIONABLE_ROLES:
        raise HTTPException(status_code=422, detail="Unsupported provisioned role")
    try:
        normalized_email = normalize_email(email)
        normalized_mobile = normalize_mobile(mobile_number) if mobile_number else None
        normalized_roll_number = (
            normalize_institutional_id(roll_number or "") if role == "student" else None
        )
        normalized_employee_code = (
            normalize_institutional_id(employee_code or "") if role == "faculty" else None
        )
        utils.validate_password(password)
    except ValueError as exc:
        if role == "student" and not (roll_number or "").strip():
            detail = "roll_number is required for students"
        elif role == "faculty" and not (employee_code or "").strip():
            detail = "employee_code is required for faculty"
        else:
            detail = str(exc)
        raise HTTPException(status_code=422, detail=detail)

    duplicate = db.query(models.User).filter(
        or_(
            func.lower(models.User.email) == normalized_email,
            normalized_identifier_expression(models.User.roll_number) == normalized_roll_number
            if normalized_roll_number
            else False,
            normalized_identifier_expression(models.User.employee_code) == normalized_employee_code
            if normalized_employee_code
            else False,
            models.User.mobile_number == normalized_mobile if normalized_mobile else False,
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Account identifier already registered")

    user = models.User(
        name=name.strip(),
        email=normalized_email,
        institutional_email=normalized_email,
        institutional_mobile=normalized_mobile,
        mobile_number=normalized_mobile,
        email_verified=True,
        mobile_verified=bool(normalized_mobile),
        mobile_is_personal=True,
        hashed_password=utils.hash_password(password),
        role=role,
        roll_number=normalized_roll_number,
        employee_code=normalized_employee_code,
        is_active=True,
        account_status=ACCOUNT_ACTIVE,
        session_version=1,
        password_changed_at=utcnow(),
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account identifier already registered")
    return user


def _create_otp_challenge(
    db: Session,
    *,
    user: models.User | None,
    purpose: str,
    channel: str,
    destination: str | None,
    subject: str,
    request_ip: str | None,
    provider: OtpDeliveryProvider,
    now: datetime | None = None,
) -> models.AuthChallenge:
    now = now or utcnow()
    subject_hash = _secret_hash(f"subject:{subject}")
    ip_hash = _request_ip_hash(request_ip)
    latest = (
        db.query(models.AuthChallenge)
        .filter(
            models.AuthChallenge.subject_hash == subject_hash,
            models.AuthChallenge.purpose == purpose,
            models.AuthChallenge.channel == channel,
        )
        .order_by(
            models.AuthChallenge.send_count.desc(),
            models.AuthChallenge.created_at.desc(),
        )
        .first()
    )

    if (
        latest
        and latest.status == "PENDING"
        and (_as_utc(latest.resend_available_at) or now) > now
    ):
        return latest

    send_count = (latest.send_count if latest else 0) + 1
    failed_attempts = latest.failed_attempts if latest else 0
    ip_count = (
        db.query(models.AuthChallenge)
        .filter(
            models.AuthChallenge.request_ip_hash == ip_hash,
            models.AuthChallenge.created_at >= now - RATE_WINDOW,
        )
        .count()
    )
    rate_limited = (
        send_count > MAX_SENDS_PER_SUBJECT
        or failed_attempts >= MAX_FAILED_ATTEMPTS
        or ip_count >= MAX_SENDS_PER_IP
    )

    if latest and latest.status in {"PENDING", "VERIFIED"}:
        latest.status = "SUPERSEDED"

    challenge_id = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = models.AuthChallenge(
        id=challenge_id,
        user_id=user.id if user else None,
        purpose=purpose,
        channel=channel,
        subject_hash=subject_hash,
        contact_hash=_contact_hash(destination) if destination else None,
        otp_hash=_otp_hash(challenge_id, code) if user and destination and not rate_limited else None,
        status="LOCKED" if rate_limited else "PENDING",
        failed_attempts=failed_attempts,
        send_count=send_count,
        expires_at=now + OTP_LIFETIME,
        resend_available_at=now + RESEND_COOLDOWN,
        request_ip_hash=ip_hash,
        delivery_status="RATE_LIMITED" if rate_limited else "PENDING",
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    if user and destination and not rate_limited:
        result = provider.send_otp(
            channel=channel,
            destination=destination,
            code=code,
            purpose=purpose,
        )
        challenge.delivery_status = "SENT" if result.delivered else "FAILED"
        challenge.failure_reason = None if result.delivered else (result.failure_reason or "Delivery failed")[:255]
        db.commit()
        db.refresh(challenge)
    elif not rate_limited:
        challenge.delivery_status = "NOT_SENT"
        challenge.failure_reason = "No eligible delivery destination"
        db.commit()
        db.refresh(challenge)
    return challenge


def verify_otp_challenge(
    db: Session,
    *,
    challenge_id: str,
    code: str,
    allowed_purposes: set[str],
    now: datetime | None = None,
) -> tuple[models.AuthChallenge, str]:
    now = now or utcnow()
    challenge = (
        db.query(models.AuthChallenge)
        .filter(models.AuthChallenge.id == challenge_id)
        .first()
    )
    valid_state = bool(
        challenge
        and challenge.purpose in allowed_purposes
        and challenge.status == "PENDING"
        and challenge.failed_attempts < MAX_FAILED_ATTEMPTS
        and (_as_utc(challenge.expires_at) or now) > now
        and challenge.otp_hash
    )
    if not valid_state or not hmac.compare_digest(challenge.otp_hash, _otp_hash(challenge_id, code)):
        if challenge and challenge.status == "PENDING":
            challenge.failed_attempts = (challenge.failed_attempts or 0) + 1
            if challenge.failed_attempts >= MAX_FAILED_ATTEMPTS:
                challenge.status = "LOCKED"
                challenge.otp_hash = None
            db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)

    authorization = secrets.token_urlsafe(40)
    challenge.status = "VERIFIED"
    challenge.otp_hash = None
    challenge.authorization_hash = _authorization_hash(authorization)
    challenge.authorization_expires_at = now + AUTHORIZATION_LIFETIME
    db.commit()
    db.refresh(challenge)
    return challenge, authorization


def authorization_challenge(
    db: Session,
    authorization: str,
    *,
    allowed_purposes: set[str],
    user_id: int | None = None,
    now: datetime | None = None,
) -> models.AuthChallenge:
    now = now or utcnow()
    challenge = (
        db.query(models.AuthChallenge)
        .filter(
            models.AuthChallenge.authorization_hash == _authorization_hash(authorization),
            models.AuthChallenge.purpose.in_(allowed_purposes),
        )
        .first()
    )
    if not (
        challenge
        and challenge.status == "VERIFIED"
        and challenge.authorization_used_at is None
        and (_as_utc(challenge.authorization_expires_at) or now) > now
        and (user_id is None or challenge.user_id == user_id)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_OTP_ERROR)
    return challenge


def start_activation(
    db: Session,
    *,
    role: str,
    institutional_id: str,
    channel: str,
    request_ip: str | None,
    provider: OtpDeliveryProvider,
) -> models.AuthChallenge:
    role = roles.normalize_role(role)
    try:
        normalized_id = normalize_institutional_id(institutional_id)
    except ValueError:
        normalized_id = "INVALID"
    matches = []
    if role in roles.PROVISIONABLE_ROLES:
        identifier_field = (
            models.User.roll_number if role == roles.STUDENT else models.User.employee_code
        )
        matches = (
            db.query(models.User)
            .filter(
                models.User.role == role,
                normalized_identifier_expression(identifier_field) == normalized_id,
            )
            .all()
        )
    user = matches[0] if len(matches) == 1 else None
    if not (
        user
        and user.account_status == ACCOUNT_PENDING
        and user.is_active is True
        and not utils.is_usable_password_hash(user.hashed_password)
    ):
        user = None

    destination = None
    if user:
        destination = user.institutional_email if channel == "email" else user.institutional_mobile
    if channel == "email" and destination:
        try:
            destination = normalize_email(destination)
        except ValueError:
            destination = None
    if channel == "mobile" and destination:
        try:
            destination = normalize_mobile(destination)
        except ValueError:
            destination = None

    return _create_otp_challenge(
        db,
        user=user,
        purpose=PURPOSE_ACTIVATION_OWNERSHIP,
        channel=channel,
        destination=destination,
        subject=f"activation:{role}:{normalized_id}",
        request_ip=request_ip,
        provider=provider,
    )


def start_activation_contact(
    db: Session,
    *,
    ownership_authorization: str,
    contact_type: str,
    contact_value: str,
    request_ip: str | None,
    provider: OtpDeliveryProvider,
) -> models.AuthChallenge:
    ownership = authorization_challenge(
        db,
        ownership_authorization,
        allowed_purposes={PURPOSE_ACTIVATION_OWNERSHIP},
    )
    if not ownership.user_id:
        raise HTTPException(status_code=400, detail=GENERIC_ACTIVATION_ERROR)

    try:
        normalized = normalize_email(contact_value) if contact_type == "email" else normalize_mobile(contact_value)
    except ValueError:
        raise HTTPException(status_code=422, detail="Enter a valid email or E.164 mobile number")

    if contact_type == "email":
        duplicate = db.query(models.User).filter(
            models.User.id != ownership.user_id,
            models.User.email_verified.is_(True),
            func.lower(models.User.email) == normalized,
        ).first()
        purpose = PURPOSE_ACTIVATION_EMAIL
    else:
        duplicate = db.query(models.User).filter(
            models.User.id != ownership.user_id,
            models.User.mobile_verified.is_(True),
            models.User.mobile_number == normalized,
        ).first()
        purpose = PURPOSE_ACTIVATION_MOBILE
    if duplicate:
        raise HTTPException(status_code=409, detail="This verified contact cannot be used")

    return _create_otp_challenge(
        db,
        user=db.query(models.User).filter(models.User.id == ownership.user_id).first(),
        purpose=purpose,
        channel=contact_type,
        destination=normalized,
        subject=f"activation-contact:{ownership.user_id}:{contact_type}",
        request_ip=request_ip,
        provider=provider,
    )


def verify_activation_contact(
    db: Session,
    *,
    ownership_authorization: str,
    contact_type: str,
    challenge_id: str,
    code: str,
) -> str:
    ownership = authorization_challenge(
        db,
        ownership_authorization,
        allowed_purposes={PURPOSE_ACTIVATION_OWNERSHIP},
    )
    purpose = PURPOSE_ACTIVATION_EMAIL if contact_type == "email" else PURPOSE_ACTIVATION_MOBILE
    challenge, authorization = verify_otp_challenge(
        db,
        challenge_id=challenge_id,
        code=code,
        allowed_purposes={purpose},
    )
    if not ownership.user_id or challenge.user_id != ownership.user_id:
        challenge.authorization_hash = None
        challenge.authorization_expires_at = None
        db.commit()
        raise HTTPException(status_code=400, detail=GENERIC_OTP_ERROR)
    return authorization


def complete_activation(
    db: Session,
    *,
    ownership_authorization: str,
    email: str,
    email_authorization: str,
    mobile_number: str,
    mobile_authorization: str,
    password: str,
    confirm_password: str,
) -> models.User:
    try:
        utils.validate_password(password, confirm_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        normalized_email = normalize_email(email)
        normalized_mobile = normalize_mobile(mobile_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    ownership = authorization_challenge(
        db,
        ownership_authorization,
        allowed_purposes={PURPOSE_ACTIVATION_OWNERSHIP},
    )
    if not ownership.user_id:
        raise HTTPException(status_code=400, detail=GENERIC_ACTIVATION_ERROR)
    email_challenge = authorization_challenge(
        db,
        email_authorization,
        allowed_purposes={PURPOSE_ACTIVATION_EMAIL},
        user_id=ownership.user_id,
    )
    mobile_challenge = authorization_challenge(
        db,
        mobile_authorization,
        allowed_purposes={PURPOSE_ACTIVATION_MOBILE},
        user_id=ownership.user_id,
    )
    if not (
        hmac.compare_digest(email_challenge.contact_hash or "", _contact_hash(normalized_email))
        and hmac.compare_digest(mobile_challenge.contact_hash or "", _contact_hash(normalized_mobile))
    ):
        raise HTTPException(status_code=400, detail="Verified contact details do not match")

    duplicate = db.query(models.User).filter(
        models.User.id != ownership.user_id,
        or_(
            and_(models.User.email_verified.is_(True), func.lower(models.User.email) == normalized_email),
            and_(models.User.mobile_verified.is_(True), models.User.mobile_number == normalized_mobile),
        ),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A verified contact is already in use")

    password_hash = utils.hash_password(password)
    now = utcnow()
    try:
        result = db.execute(
            update(models.User)
            .where(
                models.User.id == ownership.user_id,
                models.User.account_status == ACCOUNT_PENDING,
                models.User.is_active.is_(True),
                models.User.hashed_password.is_(None),
            )
            .values(
                email=normalized_email,
                mobile_number=normalized_mobile,
                email_verified=True,
                mobile_verified=True,
                mobile_is_personal=True,
                hashed_password=password_hash,
                account_status=ACCOUNT_ACTIVE,
                session_version=models.User.session_version + 1,
                password_changed_at=now,
            )
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail=GENERIC_ACTIVATION_ERROR)
        for challenge in (ownership, email_challenge, mobile_challenge):
            challenge.authorization_used_at = now
            challenge.status = "USED"
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A verified contact is already in use")

    return db.query(models.User).filter(models.User.id == ownership.user_id).first()


def start_password_reset(
    db: Session,
    *,
    identifier: str,
    channel: str,
    request_ip: str | None,
    provider: OtpDeliveryProvider,
) -> models.AuthChallenge:
    matches = find_users_by_identifier(db, identifier)
    user = matches[0] if len(matches) == 1 and account_can_authenticate(matches[0]) else None
    destination = None
    if user and channel == "email" and user.email_verified:
        destination = user.email
    elif user and channel == "mobile" and user.mobile_verified and user.mobile_is_personal:
        destination = user.mobile_number
    if not destination:
        user = None

    purpose = PURPOSE_PASSWORD_RESET_EMAIL if channel == "email" else PURPOSE_PASSWORD_RESET_MOBILE
    return _create_otp_challenge(
        db,
        user=user,
        purpose=purpose,
        channel=channel,
        destination=destination,
        subject=(
            f"password-reset:user:{user.id}:{channel}"
            if user
            else f"password-reset:unknown:{(identifier or '').strip().lower()}:{channel}"
        ),
        request_ip=request_ip,
        provider=provider,
    )


def _record_password_change_notice(
    db: Session,
    *,
    user: models.User,
    provider: OtpDeliveryProvider,
) -> None:
    subject = "Your SYS password was changed"
    message = (
        "Your SYS account password was changed. If you did not make this change, "
        "contact your SYS administrator immediately."
    )
    note = models.Notification(
        event="PASSWORD_CHANGED",
        student_id=user.id if user.role == "student" else None,
        recipients=[user.email] if user.email else [],
        subject=subject,
        body=message,
        title=subject,
        status="PENDING",
        source_module="AUTH",
        severity="WARNING",
        priority=1,
        channels=["EMAIL", "SMS", "IN_APP"],
    )
    db.add(note)
    db.flush()
    db.add(
        models.NotificationDelivery(
            notification_id=note.id,
            user_id=user.id,
            email=user.email,
            channel="IN_APP",
            status="DELIVERED",
            sent_at=utcnow(),
        )
    )
    outcomes = [True]
    for channel, destination in (("email", user.email), ("mobile", user.mobile_number)):
        verified = user.email_verified if channel == "email" else user.mobile_verified and user.mobile_is_personal
        if not destination or not verified:
            continue
        result = provider.send_security_notice(
            channel=channel,
            destination=destination,
            subject=subject,
            message=message,
        )
        db.add(
            models.NotificationDelivery(
                notification_id=note.id,
                user_id=user.id,
                email=destination if channel == "email" else None,
                channel=channel.upper(),
                status="SENT" if result.delivered else "FAILED",
                failure_reason=None if result.delivered else (result.failure_reason or "Delivery failed")[:255],
                sent_at=utcnow() if result.delivered else None,
            )
        )
        outcomes.append(result.delivered)
    note.status = "SENT" if all(outcomes) else ("PARTIAL" if any(outcomes) else "FAILED")
    db.commit()


def complete_password_reset(
    db: Session,
    *,
    reset_authorization: str,
    password: str,
    confirm_password: str,
    provider: OtpDeliveryProvider,
) -> models.User:
    try:
        utils.validate_password(password, confirm_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    challenge = authorization_challenge(
        db,
        reset_authorization,
        allowed_purposes={PURPOSE_PASSWORD_RESET_EMAIL, PURPOSE_PASSWORD_RESET_MOBILE},
    )
    user = db.query(models.User).filter(models.User.id == challenge.user_id).first()
    if not account_can_authenticate(user):
        raise HTTPException(status_code=400, detail=GENERIC_OTP_ERROR)

    now = utcnow()
    user.hashed_password = utils.hash_password(password)
    user.session_version = (user.session_version or 1) + 1
    user.password_changed_at = now
    challenge.authorization_used_at = now
    challenge.status = "USED"
    db.query(models.AuthChallenge).filter(
        models.AuthChallenge.user_id == user.id,
        models.AuthChallenge.purpose.in_({PURPOSE_PASSWORD_RESET_EMAIL, PURPOSE_PASSWORD_RESET_MOBILE}),
        models.AuthChallenge.id != challenge.id,
        models.AuthChallenge.status.in_({"PENDING", "VERIFIED"}),
    ).update({models.AuthChallenge.status: "SUPERSEDED"}, synchronize_session=False)
    db.commit()
    db.refresh(user)
    _record_password_change_notice(db, user=user, provider=provider)
    return user
