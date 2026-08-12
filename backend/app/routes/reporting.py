"""Performance sheet, report card, notifications (P0-009)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas, database
from app.academic_auth import require_course_report_access, is_admin
from app.constants import NOTIFICATION_EVENTS, RECIPIENT_TYPES, NOTIFICATION_FREQUENCIES
from app.routes.auth import get_current_user, require_roles
from app.services import reporting
from app.services import notifications as notif_svc

router = APIRouter(tags=["Reporting"])
_admin = require_roles("admin")
_staff = require_roles("admin", "faculty")


@router.get("/performance/sheet", response_model=schemas.PerformanceSheetOut)
def get_performance_sheet(
    student_id: int = Query(...),
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_course_report_access(db, current_user, course_id)
    student = db.query(models.User).filter(models.User.id == student_id, models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    sheet = reporting.build_performance_sheet(db, student_id=student_id, course_id=course_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Course or student not found")
    return sheet


@router.get("/performance/report-card")
def get_report_card(
    student_id: int = Query(...),
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_course_report_access(db, current_user, course_id)
    card = reporting.build_report_card(db, student_id=student_id, course_id=course_id)
    if not card:
        raise HTTPException(status_code=404, detail="Report card data not found")
    # Audit notification — isolated
    try:
        notif_svc.create_notification(
            db,
            event="REPORT_CARD_GENERATED",
            subject=f"Report card generated for student {student_id}",
            body=f"Report card generated for student_id={student_id} course_id={course_id}",
            course_id=course_id,
            student_id=student_id,
            dispatch=True,
        )
    except Exception:
        pass
    return card


@router.get("/performance/report-card.pdf")
def download_report_card_pdf(
    student_id: int = Query(...),
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    require_course_report_access(db, current_user, course_id)
    card = reporting.build_report_card(db, student_id=student_id, course_id=course_id)
    if not card:
        raise HTTPException(status_code=404, detail="Report card data not found")
    try:
        pdf_bytes = reporting.render_report_card_pdf(card)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    filename = f"sys_report_card_s{student_id}_c{course_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =========================
# Notification recipients (Admin)
# =========================
@router.get("/notifications/recipients", response_model=List[schemas.NotificationRecipientOut])
def list_recipients(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return db.query(models.NotificationRecipient).order_by(models.NotificationRecipient.id).all()


@router.post(
    "/notifications/recipients",
    response_model=schemas.NotificationRecipientOut,
    status_code=status.HTTP_201_CREATED,
)
def create_recipient(
    payload: schemas.NotificationRecipientCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    if payload.recipient_type not in RECIPIENT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipient_type")
    if payload.frequency not in NOTIFICATION_FREQUENCIES:
        raise HTTPException(status_code=422, detail="Invalid frequency")
    if payload.event_types:
        for e in payload.event_types:
            if e not in NOTIFICATION_EVENTS:
                raise HTTPException(status_code=422, detail=f"Invalid event: {e}")
    row = models.NotificationRecipient(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/notifications/recipients/{recipient_id}", response_model=schemas.NotificationRecipientOut)
def update_recipient(
    recipient_id: int,
    payload: schemas.NotificationRecipientUpdate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    row = db.query(models.NotificationRecipient).filter(models.NotificationRecipient.id == recipient_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Recipient not found")
    data = payload.model_dump(exclude_unset=True)
    if "recipient_type" in data and data["recipient_type"] not in RECIPIENT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipient_type")
    if "frequency" in data and data["frequency"] not in NOTIFICATION_FREQUENCIES:
        raise HTTPException(status_code=422, detail="Invalid frequency")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.get("/notifications", response_model=List[schemas.NotificationOut])
def list_notifications(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return db.query(models.Notification).order_by(models.Notification.id.desc()).limit(200).all()


@router.post("/notifications/{notification_id}/retry", response_model=schemas.NotificationOut)
def retry_notification(
    notification_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    try:
        return notif_svc.retry_notification(db, notification_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")
