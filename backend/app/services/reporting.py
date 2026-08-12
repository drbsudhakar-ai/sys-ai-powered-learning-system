"""Student performance sheet and report card builders."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models


def _pct(obtained: Optional[float], available: Optional[float]) -> Optional[float]:
    if obtained is None or available is None or available == 0:
        return None
    return round(100.0 * float(obtained) / float(available), 2)


def _attempt_subject_breakdown(db: Session, attempt: models.AssessmentAttempt) -> Dict[str, Dict[str, float]]:
    rows = (
        db.query(models.PerformanceRecord)
        .filter(models.PerformanceRecord.attempt_id == attempt.id)
        .all()
    )
    by_subject: Dict[int, Dict[str, float]] = defaultdict(lambda: {"obtained": 0.0, "available": 0.0})
    for r in rows:
        if r.subject_id is None:
            continue
        by_subject[r.subject_id]["obtained"] += float(r.marks_obtained or 0)
        by_subject[r.subject_id]["available"] += float(r.marks_available or 0)

    out: Dict[str, Dict[str, float]] = {}
    for sid, vals in by_subject.items():
        subject = db.query(models.Subject).filter(models.Subject.id == sid).first()
        name = subject.name if subject else str(sid)
        out[name] = {
            "marks_obtained": vals["obtained"],
            "marks_available": vals["available"],
            "percentage": _pct(vals["obtained"], vals["available"]),
        }
    return out


def build_performance_sheet(
    db: Session,
    *,
    student_id: int,
    course_id: int,
) -> Dict[str, Any]:
    student = db.query(models.User).filter(models.User.id == student_id, models.User.role == "student").first()
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not student or not course:
        return {}

    attempts = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.student_id == student_id,
            models.AssessmentAttempt.course_id == course_id,
        )
        .order_by(models.AssessmentAttempt.submitted_at.asc())
        .all()
    )

    buckets = {
        "TOPIC_TEST": [],
        "WEEKLY_TEST": [],
        "MONTHLY_TEST": [],
        "GRAND_TEST": [],
        "FINAL_GRAND_TEST": [],
    }
    subject_acc: Dict[str, List[float]] = defaultdict(list)

    for attempt in attempts:
        assessment = attempt.assessment
        a_type = (assessment.assessment_type if assessment else None) or "TOPIC_TEST"
        subject_marks = _attempt_subject_breakdown(db, attempt)
        for sname, vals in subject_marks.items():
            if vals.get("percentage") is not None:
                subject_acc[sname].append(vals["percentage"])

        entry = {
            "attempt_id": attempt.id,
            "assessment_id": attempt.assessment_id,
            "assessment_version_id": attempt.version_id,
            "title": assessment.title if assessment else "",
            "assessment_type": a_type,
            "assessment_category": assessment.category if assessment else None,
            "date": attempt.submitted_at,
            "marks_obtained": attempt.total_marks_obtained,
            "marks_available": attempt.total_marks_available,
            "percentage": _pct(attempt.total_marks_obtained, attempt.total_marks_available),
            "subject_marks": subject_marks,
            "topic_id": assessment.topic_id if assessment else None,
            "subject_id": assessment.subject_id if assessment else None,
        }
        if a_type in buckets:
            buckets[a_type].append(entry)
        else:
            buckets["TOPIC_TEST"].append(entry)

    subject_summary = []
    for name, pcts in subject_acc.items():
        subject_summary.append(
            {
                "subject": name,
                "average_percentage": round(sum(pcts) / len(pcts), 2) if pcts else None,
                "assessments_count": len(pcts),
            }
        )

    all_pcts = [
        e["percentage"]
        for group in buckets.values()
        for e in group
        if e.get("percentage") is not None
    ]
    overall = {
        "total_assessments": sum(len(v) for v in buckets.values()),
        "completed_assessments": sum(len(v) for v in buckets.values()),
        "average_percentage": round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else None,
        "latest_percentage": all_pcts[-1] if all_pcts else None,
        "final_grand_percentage": buckets["FINAL_GRAND_TEST"][-1]["percentage"]
        if buckets["FINAL_GRAND_TEST"]
        else None,
    }

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "roll_number": student.roll_number,
        },
        "course": {"id": course.id, "title": course.title},
        "topic_assessments": buckets["TOPIC_TEST"],
        "weekly_tests": buckets["WEEKLY_TEST"],
        "monthly_tests": buckets["MONTHLY_TEST"],
        "grand_tests": buckets["GRAND_TEST"],
        "final_grand_tests": buckets["FINAL_GRAND_TEST"],
        "subject_summary": subject_summary,
        "overall_summary": overall,
    }


def build_report_card(db: Session, *, student_id: int, course_id: int) -> Dict[str, Any]:
    sheet = build_performance_sheet(db, student_id=student_id, course_id=course_id)
    if not sheet:
        return {}
    return {
        "student": sheet["student"],
        "course": sheet["course"],
        "academic_period": None,
        "assessment_summary": {
            "topic": sheet["topic_assessments"],
            "weekly": sheet["weekly_tests"],
            "monthly": sheet["monthly_tests"],
            "grand": sheet["grand_tests"],
            "final_grand": sheet["final_grand_tests"],
        },
        "subject_performance": sheet["subject_summary"],
        "overall_performance": sheet["overall_summary"],
    }


def render_report_card_pdf(report: Dict[str, Any]) -> bytes:
    """Generate a simple SYS-branded PDF. Uses reportlab if available."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is required for PDF generation") from exc

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "SYS — Strengthen Your Skills")
    y -= 24
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Student Report Card")
    y -= 30

    student = report.get("student") or {}
    course = report.get("course") or {}
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Student: {student.get('name', '')}")
    y -= 16
    c.drawString(40, y, f"Roll / ID: {student.get('roll_number') or student.get('id', '')}")
    y -= 16
    c.drawString(40, y, f"Course: {course.get('title', '')}")
    y -= 28

    overall = report.get("overall_performance") or {}
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Overall Performance")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Assessments: {overall.get('total_assessments', 0)}")
    y -= 14
    c.drawString(40, y, f"Average: {overall.get('average_percentage')}%")
    y -= 14
    c.drawString(40, y, f"Latest: {overall.get('latest_percentage')}%")
    y -= 14
    c.drawString(40, y, f"Final Grand: {overall.get('final_grand_percentage')}%")
    y -= 28

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Subject Performance")
    y -= 16
    c.setFont("Helvetica", 11)
    for row in report.get("subject_performance") or []:
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)
        c.drawString(
            40,
            y,
            f"{row.get('subject')}: avg {row.get('average_percentage')}% "
            f"({row.get('assessments_count')} assessments)",
        )
        y -= 14

    summary = report.get("assessment_summary") or {}
    for label, key in [
        ("Topic Tests", "topic"),
        ("Weekly Tests", "weekly"),
        ("Monthly Tests", "monthly"),
        ("Grand Tests", "grand"),
        ("Final Grand Tests", "final_grand"),
    ]:
        items = summary.get(key) or []
        if not items:
            continue
        y -= 10
        if y < 80:
            c.showPage()
            y = height - 50
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, label)
        y -= 16
        c.setFont("Helvetica", 10)
        for item in items:
            if y < 60:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(
                50,
                y,
                f"{item.get('title')} — {item.get('marks_obtained')}/{item.get('marks_available')} "
                f"({item.get('percentage')}%)",
            )
            y -= 13

    c.showPage()
    c.save()
    return buffer.getvalue()
