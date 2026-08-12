"""P0-012 Performance Analyzer + in-app notification APIs."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.academic_auth import is_admin, is_course_coordinator, can_access_course_questions
from app.routes.auth import get_current_user, require_roles
from app.services import performance_analyzer as analyzer
from app.services import notifications as notif_svc
from app.services import reporting

router = APIRouter(tags=["Performance Analyzer"])
_staff = require_roles("admin", "faculty")


def _authorize_student_course(db: Session, user: models.User, student_id: int, course_id: int) -> None:
    if not notif_svc.user_can_view_student_performance(db, user, student_id, course_id):
        raise HTTPException(status_code=403, detail="Not authorized for this student/course performance")


@router.get("/analyzer/students/{student_id}/courses/{course_id}")
def get_performance_analysis(
    student_id: int,
    course_id: int,
    refresh: bool = Query(False),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    if not refresh:
        cached = (
            db.query(models.PerformanceAnalysis)
            .filter(
                models.PerformanceAnalysis.student_id == student_id,
                models.PerformanceAnalysis.course_id == course_id,
            )
            .first()
        )
        if cached and cached.analysis_json:
            return cached.analysis_json
    analysis = analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis available")
    return analysis


@router.get("/analyzer/students/{student_id}/courses/{course_id}/profile")
def get_learning_profile(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    row = (
        db.query(models.StudentLearningProfile)
        .filter(
            models.StudentLearningProfile.student_id == student_id,
            models.StudentLearningProfile.course_id == course_id,
        )
        .first()
    )
    if not row:
        analysis = analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
        if not analysis:
            raise HTTPException(status_code=404, detail="Profile not available")
        return analysis.get("profile")
    return row.profile_json


@router.get("/analyzer/students/{student_id}/courses/{course_id}/gaps")
def get_learning_gaps(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    rows = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
        )
        .order_by(models.LearningGap.is_high_priority.desc(), models.LearningGap.id)
        .all()
    )
    if not rows:
        analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
        rows = (
            db.query(models.LearningGap)
            .filter(
                models.LearningGap.student_id == student_id,
                models.LearningGap.course_id == course_id,
            )
            .all()
        )
    return [
        {
            "id": r.id,
            "scope_type": r.scope_type,
            "scope_id": r.scope_id,
            "scope_name": r.scope_name,
            "classification": r.classification,
            "confidence": r.confidence,
            "priority_score": r.priority_score,
            "is_high_priority": r.is_high_priority,
            "observed_evidence": r.evidence,
            "system_inference": r.inference,
        }
        for r in rows
    ]


@router.get("/analyzer/students/{student_id}/courses/{course_id}/readiness")
def get_readiness(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    analysis = analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
    if not analysis:
        raise HTTPException(status_code=404, detail="Readiness not available")
    return analysis.get("readiness")


@router.get("/analyzer/students/{student_id}/courses/{course_id}/report")
def get_analyzer_report(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    analysis = analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
    if not analysis:
        raise HTTPException(status_code=404, detail="Report not available")
    return reporting.build_analyzer_performance_report(analysis)


@router.get("/analyzer/students/{student_id}/courses/{course_id}/report.pdf")
def download_analyzer_report_pdf(
    student_id: int,
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _authorize_student_course(db, current_user, student_id, course_id)
    analysis = analyzer.analyze_student_course(db, student_id=student_id, course_id=course_id, persist=True)
    if not analysis:
        raise HTTPException(status_code=404, detail="Report not available")
    report = reporting.build_analyzer_performance_report(analysis)
    pdf = reporting.render_analyzer_report_pdf(report)
    filename = f"sys_performance_report_s{student_id}_c{course_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/analyzer/me")
def my_performance_summary(
    course_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if (current_user.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    analysis = analyzer.analyze_student_course(
        db, student_id=current_user.id, course_id=course_id, persist=True
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No performance data yet")
    return {
        "overall": analysis.get("overall"),
        "strengths": analysis.get("strengths"),
        "learning_gaps": analysis.get("learning_gaps"),
        "high_priority_gaps": analysis.get("high_priority_gaps"),
        "readiness": analysis.get("readiness"),
        "trends": analysis.get("trends"),
        "recommended_focus": analysis.get("recommended_focus"),
        "assessment_type_performance": analysis.get("assessment_type_performance"),
    }


@router.get("/analyzer/courses/{course_id}/attention")
def course_students_needing_attention(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    if not is_admin(current_user) and not is_course_coordinator(db, current_user, course_id):
        if not can_access_course_questions(db, current_user, course_id):
            raise HTTPException(status_code=403, detail="Not authorized")
    rows = (
        db.query(models.PerformanceAnalysis)
        .filter(models.PerformanceAnalysis.course_id == course_id)
        .all()
    )
    attention = []
    high = []
    for r in rows:
        a = r.analysis_json or {}
        gaps = a.get("high_priority_gaps") or []
        item = {
            "student_id": r.student_id,
            "overall_percentage": r.overall_percentage,
            "trend": r.trend,
            "readiness_estimate": r.readiness_estimate,
            "high_priority_gap_count": len(gaps),
        }
        if r.trend == "DECLINING" or gaps:
            attention.append(item)
        if (r.overall_percentage or 0) >= 80 and r.trend in ("IMPROVING", "STABLE"):
            high.append(item)
    return {"needs_attention": attention, "high_performing": high}


# ---- In-app notifications ----

@router.get("/inbox/notifications")
def inbox_list(
    unread_only: bool = Query(False),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return notif_svc.list_inbox(db, current_user, unread_only=unread_only)


@router.get("/inbox/unread-count")
def inbox_unread(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return {"unread": notif_svc.unread_count(db, current_user)}


@router.post("/inbox/notifications/{delivery_id}/read")
def inbox_mark_read(
    delivery_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        return notif_svc.mark_read(db, current_user, delivery_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/inbox/notifications/read-all")
def inbox_mark_all(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return notif_svc.mark_all_read(db, current_user)


@router.get("/inbox/preferences")
def get_prefs(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = notif_svc.get_or_create_preferences(db, current_user.id)
    return [
        {
            "id": r.id,
            "category": r.category,
            "email_enabled": r.email_enabled,
            "in_app_enabled": r.in_app_enabled,
            "sms_enabled": r.sms_enabled,
        }
        for r in rows
    ]


@router.put("/inbox/preferences")
def put_prefs(
    payload: List[schemas.NotificationPreferenceIn],
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    notif_svc.get_or_create_preferences(db, current_user.id)
    for item in payload:
        row = (
            db.query(models.NotificationPreference)
            .filter(
                models.NotificationPreference.user_id == current_user.id,
                models.NotificationPreference.category == item.category,
            )
            .first()
        )
        if not row:
            continue
        if item.email_enabled is not None:
            row.email_enabled = item.email_enabled
        if item.in_app_enabled is not None:
            row.in_app_enabled = item.in_app_enabled
        if item.sms_enabled is not None:
            row.sms_enabled = item.sms_enabled
    db.commit()
    rows = notif_svc.get_or_create_preferences(db, current_user.id)
    return [
        {
            "id": r.id,
            "category": r.category,
            "email_enabled": r.email_enabled,
            "in_app_enabled": r.in_app_enabled,
            "sms_enabled": r.sms_enabled,
        }
        for r in rows
    ]
