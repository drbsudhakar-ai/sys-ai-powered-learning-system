"""Unified Notification Engine (P0-012) — extends P0-009 email foundation.

Channels: EMAIL, IN_APP (SMS stubbed for future).
"""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy.orm import Session, joinedload

from app import models
from app.academic_auth import can_access_course_questions, is_admin, is_course_coordinator, is_subject_expert
from app.constants import (
    MAX_NOTIFICATION_RETRIES,
    NOTIFICATION_EVENTS,
    NOTIFICATION_PREF_CATEGORIES,
)

EVENT_CATEGORY = {
    "ASSESSMENT_PUBLISHED": "ASSESSMENT_RESULTS",
    "ASSESSMENT_COMPLETED": "ASSESSMENT_RESULTS",
    "ASSESSMENT_EVALUATED": "ASSESSMENT_RESULTS",
    "RESULT_AVAILABLE": "ASSESSMENT_RESULTS",
    "RESULTS_PUBLISHED": "ASSESSMENT_RESULTS",
    "ANSWER_KEY_AVAILABLE": "ASSESSMENT_RESULTS",
    "ASSESSMENT_REMINDER": "ROUTINE",
    "PERFORMANCE_ANALYSIS_AVAILABLE": "PERFORMANCE_REPORTS",
    "WEEKLY_PERFORMANCE_REPORT": "PERFORMANCE_REPORTS",
    "MONTHLY_PERFORMANCE_REPORT": "PERFORMANCE_REPORTS",
    "GRAND_ASSESSMENT_ANALYSIS": "PERFORMANCE_REPORTS",
    "FINAL_GRAND_ASSESSMENT_ANALYSIS": "PERFORMANCE_REPORTS",
    "REPORT_GENERATED": "PERFORMANCE_REPORTS",
    "REPORT_CARD_GENERATED": "PERFORMANCE_REPORTS",
    "EXAM_READINESS_UPDATED": "PERFORMANCE_REPORTS",
    "SIGNIFICANT_PERFORMANCE_DECLINE": "IMPORTANT_ALERTS",
    "CRITICAL_LEARNING_GAP": "IMPORTANT_ALERTS",
    "REPEATED_WEAKNESS": "IMPORTANT_ALERTS",
    "SIGNIFICANT_IMPROVEMENT": "IMPORTANT_ALERTS",
    "SYSTEM_ALERT": "IMPORTANT_ALERTS",
    "ACADEMIC_ANNOUNCEMENT": "ROUTINE",
    "LEARNING_RECOMMENDATION": "ROUTINE",
    "REMEDIAL_PLAN_AVAILABLE": "ROUTINE",
    "REMEDIAL_GROUP_ASSIGNED": "ROUTINE",
    "REMEDIAL_INTERVENTION_ASSIGNED": "ROUTINE",
    "REMEDIAL_SESSION_AVAILABLE": "ROUTINE",
    "REMEDIAL_INTERVENTION_COMPLETED": "ROUTINE",
    "REMEDIAL_REASSESSMENT_REQUIRED": "IMPORTANT_ALERTS",
}

MANDATORY_EVENTS = {
    "SYSTEM_ALERT",
    "CRITICAL_LEARNING_GAP",
    "SIGNIFICANT_PERFORMANCE_DECLINE",
}


class NotificationChannel:
    name = "BASE"

    def send(self, db: Session, delivery: models.NotificationDelivery, note: models.Notification) -> None:
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    name = "EMAIL"

    def send(self, db: Session, delivery: models.NotificationDelivery, note: models.Notification) -> None:
        to_addr = delivery.email
        if not to_addr and delivery.user_id:
            user = db.query(models.User).filter(models.User.id == delivery.user_id).first()
            to_addr = user.email if user else None
        if not to_addr:
            raise RuntimeError("No email address for delivery")
        if not _smtp_configured():
            raise RuntimeError("SMTP not configured")
        send_email([to_addr], note.subject or note.title or note.event, note.body or "")


class InAppChannel(NotificationChannel):
    name = "IN_APP"

    def send(self, db: Session, delivery: models.NotificationDelivery, note: models.Notification) -> None:
        if not delivery.user_id:
            raise RuntimeError("IN_APP requires user_id")
        # Persistence of delivery row is the in-app inbox item.
        return None


class SMSChannel(NotificationChannel):
    """Future SMS channel stub — not implemented."""

    name = "SMS"

    def send(self, db: Session, delivery: models.NotificationDelivery, note: models.Notification) -> None:
        raise RuntimeError("SMS channel not implemented")


CHANNELS = {
    "EMAIL": EmailChannel(),
    "IN_APP": InAppChannel(),
    "SMS": SMSChannel(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def send_email(to_addrs: Iterable[str], subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM")
    if not host or not from_addr:
        raise RuntimeError("SMTP not configured (set SMTP_HOST and SMTP_FROM)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)


def resolve_recipient_emails(
    db: Session,
    event: str,
    course_id: Optional[int] = None,
) -> List[str]:
    """P0-009 compatible email list (admins + coordinators + configured recipients)."""
    users = resolve_recipient_users(db, event=event, course_id=course_id, student_id=None, include_student=False)
    emails = [u.email for u in users if u.email]
    rows = (
        db.query(models.NotificationRecipient)
        .filter(models.NotificationRecipient.is_active.is_(True))
        .all()
    )
    for r in rows:
        if r.course_id and course_id and r.course_id != course_id:
            continue
        events = r.event_types or []
        if events and event not in events:
            continue
        if r.email and r.email not in emails:
            emails.append(r.email)
    return emails


def resolve_recipient_users(
    db: Session,
    *,
    event: str,
    course_id: Optional[int],
    student_id: Optional[int],
    include_student: bool = True,
) -> List[models.User]:
    found: Dict[int, models.User] = {}

    def _add(u: Optional[models.User]):
        if u and u.is_active and u.id not in found:
            found[u.id] = u

    if include_student and student_id:
        _add(db.query(models.User).filter(models.User.id == student_id).first())

    if course_id:
        coords = (
            db.query(models.User)
            .join(
                models.FacultyCourseAssignment,
                models.FacultyCourseAssignment.faculty_id == models.User.id,
            )
            .filter(models.FacultyCourseAssignment.course_id == course_id)
            .all()
        )
        for u in coords:
            _add(u)

        # Subject experts for subjects in course (scoped academic alerts)
        if event in (
            "CRITICAL_LEARNING_GAP",
            "REPEATED_WEAKNESS",
            "PERFORMANCE_ANALYSIS_AVAILABLE",
            "SIGNIFICANT_PERFORMANCE_DECLINE",
            "GRAND_ASSESSMENT_ANALYSIS",
            "FINAL_GRAND_ASSESSMENT_ANALYSIS",
            "REMEDIAL_PLAN_AVAILABLE",
            "REMEDIAL_GROUP_ASSIGNED",
            "REMEDIAL_INTERVENTION_ASSIGNED",
            "REMEDIAL_SESSION_AVAILABLE",
            "REMEDIAL_INTERVENTION_COMPLETED",
            "REMEDIAL_REASSESSMENT_REQUIRED",
        ):
            subjects = db.query(models.Subject.id).filter(models.Subject.course_id == course_id).all()
            for (sid,) in subjects:
                experts = (
                    db.query(models.User)
                    .join(
                        models.SubjectExpertAssignment,
                        models.SubjectExpertAssignment.faculty_id == models.User.id,
                    )
                    .filter(models.SubjectExpertAssignment.subject_id == sid)
                    .all()
                )
                for u in experts:
                    _add(u)

    for u in db.query(models.User).filter(models.User.role == "admin", models.User.is_active.is_(True)).all():
        _add(u)

    return list(found.values())


def _pref_allows(db: Session, user_id: int, event: str, channel: str) -> bool:
    if event in MANDATORY_EVENTS:
        return True
    category = EVENT_CATEGORY.get(event, "ROUTINE")
    pref = (
        db.query(models.NotificationPreference)
        .filter(
            models.NotificationPreference.user_id == user_id,
            models.NotificationPreference.category == category,
        )
        .first()
    )
    if not pref:
        return True
    if channel == "EMAIL":
        return bool(pref.email_enabled)
    if channel == "IN_APP":
        return bool(pref.in_app_enabled)
    if channel == "SMS":
        return bool(pref.sms_enabled)
    return True


def emit_event(
    db: Session,
    *,
    event: str,
    title: str,
    message: str,
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    severity: str = "INFO",
    priority: int = 5,
    link_path: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    source_module: str = "SYSTEM",
    channels: Optional[List[str]] = None,
    dispatch: bool = True,
) -> models.Notification:
    """Unified entry point for any SYS module."""
    if event not in NOTIFICATION_EVENTS:
        raise ValueError(f"Invalid notification event: {event}")

    channels = channels or ["EMAIL", "IN_APP"]
    users = resolve_recipient_users(
        db, event=event, course_id=course_id, student_id=student_id, include_student=True
    )
    emails = [u.email for u in users if u.email]
    # configured external recipients (email-only)
    for e in resolve_recipient_emails(db, event, course_id):
        if e not in emails:
            emails.append(e)

    note = models.Notification(
        event=event,
        assessment_id=assessment_id,
        course_id=course_id,
        student_id=student_id,
        recipients=emails,
        subject=title,
        body=message,
        title=title,
        status="PENDING",
        retry_count=0,
        source_module=source_module,
        severity=severity,
        priority=priority,
        payload=payload,
        link_path=link_path,
        channels=channels,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # Create delivery rows
    user_by_email = {u.email.lower(): u for u in users if u.email}
    for ch in channels:
        if ch == "SMS":
            continue  # architected, not delivered
        if ch == "IN_APP":
            for u in users:
                if not _pref_allows(db, u.id, event, "IN_APP"):
                    continue
                db.add(
                    models.NotificationDelivery(
                        notification_id=note.id,
                        user_id=u.id,
                        email=u.email,
                        channel="IN_APP",
                        status="PENDING",
                    )
                )
        elif ch == "EMAIL":
            seen: Set[str] = set()
            for email in emails:
                if not email or email.lower() in seen:
                    continue
                seen.add(email.lower())
                user = user_by_email.get(email.lower())
                if user and not _pref_allows(db, user.id, event, "EMAIL"):
                    continue
                db.add(
                    models.NotificationDelivery(
                        notification_id=note.id,
                        user_id=user.id if user else None,
                        email=email,
                        channel="EMAIL",
                        status="PENDING",
                    )
                )
    db.commit()

    if dispatch:
        dispatch_notification(db, note.id)
        db.refresh(note)
    return note


def create_notification(
    db: Session,
    *,
    event: str,
    subject: str,
    body: str,
    assessment_id: Optional[int] = None,
    course_id: Optional[int] = None,
    student_id: Optional[int] = None,
    dispatch: bool = True,
) -> models.Notification:
    """Backward-compatible P0-009 API."""
    return emit_event(
        db,
        event=event,
        title=subject,
        message=body,
        assessment_id=assessment_id,
        course_id=course_id,
        student_id=student_id,
        channels=["EMAIL", "IN_APP"],
        dispatch=dispatch,
        source_module="LEGACY",
    )


def dispatch_notification(db: Session, notification_id: int) -> models.Notification:
    note = (
        db.query(models.Notification)
        .options(joinedload(models.Notification.deliveries))
        .filter(models.Notification.id == notification_id)
        .first()
    )
    if not note:
        raise ValueError("Notification not found")

    note.status = "PROCESSING"
    db.commit()

    deliveries = (
        db.query(models.NotificationDelivery)
        .filter(models.NotificationDelivery.notification_id == note.id)
        .all()
    )
    if not deliveries:
        # Legacy path: email-only blast to recipients list
        try:
            if not note.recipients:
                raise RuntimeError("No recipients configured")
            if not _smtp_configured():
                note.status = "FAILED"
                note.failure_reason = "SMTP not configured"
                note.retry_count = (note.retry_count or 0) + 1
            else:
                send_email(note.recipients, note.subject or note.event, note.body or "")
                note.status = "SENT"
                note.sent_at = _utcnow()
                note.failure_reason = None
        except Exception as exc:  # noqa: BLE001
            note.status = "FAILED"
            note.failure_reason = str(exc)[:500]
            note.retry_count = (note.retry_count or 0) + 1
        db.commit()
        db.refresh(note)
        return note

    sent = failed = 0
    for d in deliveries:
        if d.status in ("SENT", "DELIVERED", "READ"):
            sent += 1
            continue
        channel = CHANNELS.get(d.channel)
        if not channel:
            d.status = "FAILED"
            d.failure_reason = f"Unknown channel {d.channel}"
            failed += 1
            continue
        try:
            channel.send(db, d, note)
            d.status = "SENT"
            d.sent_at = _utcnow()
            d.failure_reason = None
            # Email: SMTP success != verified delivery
            if d.channel == "EMAIL":
                d.status = "SENT"
            elif d.channel == "IN_APP":
                d.status = "DELIVERED"
            sent += 1
        except Exception as exc:  # noqa: BLE001
            d.status = "FAILED"
            d.failure_reason = str(exc)[:500]
            d.retry_count = (d.retry_count or 0) + 1
            failed += 1

    if failed and sent:
        note.status = "PARTIAL"
    elif failed and not sent:
        note.status = "FAILED"
        note.failure_reason = "All channel deliveries failed"
        note.retry_count = (note.retry_count or 0) + 1
    else:
        note.status = "SENT"
        note.sent_at = _utcnow()
        note.failure_reason = None
    db.commit()
    db.refresh(note)
    return note


def retry_notification(db: Session, notification_id: int) -> models.Notification:
    note = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not note:
        raise ValueError("Notification not found")
    if (note.retry_count or 0) >= MAX_NOTIFICATION_RETRIES:
        note.status = "FAILED"
        note.failure_reason = f"Max retries ({MAX_NOTIFICATION_RETRIES}) exceeded"
        db.commit()
        db.refresh(note)
        return note
    note.status = "RETRYING"
    db.commit()
    # reset failed deliveries under retry budget
    for d in (
        db.query(models.NotificationDelivery)
        .filter(
            models.NotificationDelivery.notification_id == note.id,
            models.NotificationDelivery.status == "FAILED",
        )
        .all()
    ):
        if (d.retry_count or 0) < MAX_NOTIFICATION_RETRIES:
            d.status = "PENDING"
    db.commit()
    return dispatch_notification(db, notification_id)


def list_inbox(db: Session, user: models.User, *, unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
    q = (
        db.query(models.NotificationDelivery)
        .options(joinedload(models.NotificationDelivery.notification))
        .filter(
            models.NotificationDelivery.user_id == user.id,
            models.NotificationDelivery.channel == "IN_APP",
        )
        .order_by(models.NotificationDelivery.id.desc())
    )
    if unread_only:
        q = q.filter(models.NotificationDelivery.is_read.is_(False))
    rows = q.limit(limit).all()
    out = []
    for d in rows:
        n = d.notification
        out.append(
            {
                "delivery_id": d.id,
                "notification_id": n.id if n else None,
                "event": n.event if n else None,
                "title": (n.title or n.subject) if n else None,
                "message": n.body if n else None,
                "severity": n.severity if n else None,
                "link_path": n.link_path if n else None,
                "payload": n.payload if n else None,
                "is_read": d.is_read,
                "status": d.status,
                "created_at": d.created_at,
                "read_at": d.read_at,
                "student_id": n.student_id if n else None,
                "course_id": n.course_id if n else None,
            }
        )
    return out


def unread_count(db: Session, user: models.User) -> int:
    return (
        db.query(models.NotificationDelivery)
        .filter(
            models.NotificationDelivery.user_id == user.id,
            models.NotificationDelivery.channel == "IN_APP",
            models.NotificationDelivery.is_read.is_(False),
        )
        .count()
    )


def mark_read(db: Session, user: models.User, delivery_id: int) -> Dict[str, Any]:
    d = (
        db.query(models.NotificationDelivery)
        .filter(
            models.NotificationDelivery.id == delivery_id,
            models.NotificationDelivery.user_id == user.id,
        )
        .first()
    )
    if not d:
        raise ValueError("Notification not found")
    d.is_read = True
    d.read_at = _utcnow()
    d.status = "READ"
    db.commit()
    return {"ok": True, "delivery_id": d.id}


def mark_all_read(db: Session, user: models.User) -> Dict[str, Any]:
    rows = (
        db.query(models.NotificationDelivery)
        .filter(
            models.NotificationDelivery.user_id == user.id,
            models.NotificationDelivery.channel == "IN_APP",
            models.NotificationDelivery.is_read.is_(False),
        )
        .all()
    )
    now = _utcnow()
    for d in rows:
        d.is_read = True
        d.read_at = now
        d.status = "READ"
    db.commit()
    return {"ok": True, "marked": len(rows)}


def get_or_create_preferences(db: Session, user_id: int) -> List[models.NotificationPreference]:
    existing = (
        db.query(models.NotificationPreference)
        .filter(models.NotificationPreference.user_id == user_id)
        .all()
    )
    have = {p.category for p in existing}
    for cat in NOTIFICATION_PREF_CATEGORIES:
        if cat not in have:
            db.add(
                models.NotificationPreference(
                    user_id=user_id,
                    category=cat,
                    email_enabled=True,
                    in_app_enabled=True,
                    sms_enabled=False,
                )
            )
    db.commit()
    return (
        db.query(models.NotificationPreference)
        .filter(models.NotificationPreference.user_id == user_id)
        .order_by(models.NotificationPreference.category)
        .all()
    )


def user_can_view_student_performance(db: Session, user: models.User, student_id: int, course_id: int) -> bool:
    role = (user.role or "").lower()
    if role == "student":
        return user.id == student_id
    if is_admin(user):
        return True
    if is_course_coordinator(db, user, course_id):
        return True
    if can_access_course_questions(db, user, course_id):
        return True
    return False
