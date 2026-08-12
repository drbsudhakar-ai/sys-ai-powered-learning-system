"""Email notification service — failure isolated from assessment persistence."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.constants import NOTIFICATION_EVENTS


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
    rows = (
        db.query(models.NotificationRecipient)
        .filter(models.NotificationRecipient.is_active.is_(True))
        .all()
    )
    emails: List[str] = []
    for r in rows:
        if r.course_id and course_id and r.course_id != course_id:
            continue
        events = r.event_types or []
        if events and event not in events:
            continue
        emails.append(r.email)

    # Course coordinators for the course (email from User)
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
            if u.email and u.email not in emails:
                emails.append(u.email)

    # Active admins
    admins = db.query(models.User).filter(models.User.role == "admin", models.User.is_active.is_(True)).all()
    for u in admins:
        if u.email and u.email not in emails:
            emails.append(u.email)

    return emails


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
    if event not in NOTIFICATION_EVENTS:
        raise ValueError(f"Invalid notification event: {event}")

    recipients = resolve_recipient_emails(db, event, course_id)
    note = models.Notification(
        event=event,
        assessment_id=assessment_id,
        course_id=course_id,
        student_id=student_id,
        recipients=recipients,
        subject=subject,
        body=body,
        status="PENDING",
        retry_count=0,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    if dispatch:
        dispatch_notification(db, note.id)
        db.refresh(note)
    return note


def dispatch_notification(db: Session, notification_id: int) -> models.Notification:
    note = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not note:
        raise ValueError("Notification not found")

    note.status = "PROCESSING"
    db.commit()

    try:
        if not note.recipients:
            raise RuntimeError("No recipients configured")
        if not _smtp_configured():
            # Soft-fail: record as failed without raising to callers that ignore return
            note.status = "FAILED"
            note.failure_reason = "SMTP not configured"
            note.retry_count = (note.retry_count or 0) + 1
            db.commit()
            db.refresh(note)
            return note
        send_email(note.recipients, note.subject or note.event, note.body or "")
        note.status = "SENT"
        note.sent_at = datetime.now(timezone.utc)
        note.failure_reason = None
        db.commit()
    except Exception as exc:  # noqa: BLE001 — isolate delivery failures
        note.status = "FAILED"
        note.failure_reason = str(exc)[:500]
        note.retry_count = (note.retry_count or 0) + 1
        db.commit()

    db.refresh(note)
    return note


def retry_notification(db: Session, notification_id: int) -> models.Notification:
    note = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not note:
        raise ValueError("Notification not found")
    note.status = "RETRYING"
    db.commit()
    return dispatch_notification(db, notification_id)
