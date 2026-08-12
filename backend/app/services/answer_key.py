"""Answer Key + Explanation PDF from immutable assessment version snapshots."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models


def build_answer_key_payload(db: Session, version: models.AssessmentVersion) -> Dict[str, Any]:
    assessment = version.assessment or db.query(models.Assessment).get(version.assessment_id)
    course = None
    if assessment:
        course = db.query(models.Course).filter(models.Course.id == assessment.course_id).first()
    questions = (
        db.query(models.AssessmentQuestion)
        .filter(models.AssessmentQuestion.version_id == version.id)
        .order_by(models.AssessmentQuestion.sequence)
        .all()
    )
    items: List[Dict[str, Any]] = []
    for aq in questions:
        items.append(
            {
                "sequence": aq.sequence,
                "stem": aq.stem_snapshot or "",
                "options": aq.options_snapshot or [],
                "correct_answer": aq.correct_answer_snapshot or "",
                "explanation": aq.explanation_snapshot or "",
                "shortcut": aq.shortcut_snapshot,
                "alternative_solution": aq.alternative_solution_snapshot,
                "common_traps": aq.common_traps_snapshot,
                "marks": aq.marks_available,
                "negative_marks": aq.negative_marks_snapshot,
                "difficulty": aq.difficulty,
                "subject": aq.subject_name_snapshot,
                "topic": aq.topic_name_snapshot,
                "question_type": aq.question_type_snapshot,
            }
        )
    return {
        "course": course.title if course else None,
        "assessment_title": assessment.title if assessment else None,
        "assessment_type": version.assessment_type or (assessment.assessment_type if assessment else None),
        "version_number": version.version_number,
        "published_at": version.published_at,
        "total_questions": version.total_questions or len(items),
        "total_marks": version.total_marks,
        "questions": items,
        "disclaimer": "Answer key for the administered assessment version. Historical content is immutable.",
    }


def render_answer_key_pdf(payload: Dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle("SYS Answer Key and Explanations")
    c.setAuthor("SYS - Strengthen Your Skills")
    c.setSubject(payload.get("assessment_title") or "Answer Key")
    width, height = A4
    y = height - 50

    def newline(size=11, gap=14):
        nonlocal y
        y -= gap
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", size)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "SYS — Strengthen Your Skills")
    newline(16, 22)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Answer Key & Explanations")
    newline(12, 18)
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Course: {payload.get('course') or '—'}")
    newline()
    c.drawString(40, y, f"Assessment: {payload.get('assessment_title') or '—'}")
    newline()
    c.drawString(
        40,
        y,
        f"Type: {payload.get('assessment_type') or '—'}  |  Version: v{payload.get('version_number')}",
    )
    newline()
    c.drawString(
        40,
        y,
        f"Questions: {payload.get('total_questions')}  |  Total marks: {payload.get('total_marks')}",
    )
    newline(10, 12)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, y, payload.get("disclaimer") or "")
    newline(11, 18)

    for q in payload.get("questions") or []:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"Q{q.get('sequence')}. ({q.get('marks')} marks)")
        newline(10, 13)
        c.setFont("Helvetica", 10)
        stem = (q.get("stem") or "")[:900]
        # wrap roughly
        while stem:
            line, stem = stem[:95], stem[95:]
            c.drawString(45, y, line)
            newline(10, 12)
        meta = " · ".join(
            x for x in [q.get("subject"), q.get("topic"), q.get("difficulty"), q.get("question_type")] if x
        )
        if meta:
            c.setFont("Helvetica", 9)
            c.drawString(45, y, meta)
            newline(9, 12)
        for opt in q.get("options") or []:
            c.setFont("Helvetica", 10)
            c.drawString(55, y, f"• {str(opt)[:90]}")
            newline(10, 12)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45, y, f"Correct answer: {q.get('correct_answer') or '—'}")
        newline(10, 12)
        if q.get("explanation"):
            c.setFont("Helvetica", 9)
            expl = f"Explanation: {q['explanation']}"[:500]
            while expl:
                line, expl = expl[:95], expl[95:]
                c.drawString(45, y, line)
                newline(9, 11)
        if q.get("shortcut"):
            c.setFont("Helvetica", 9)
            c.drawString(45, y, f"Shortcut: {str(q['shortcut'])[:90]}")
            newline(9, 11)
        if q.get("alternative_solution"):
            c.setFont("Helvetica", 9)
            c.drawString(45, y, f"Alt solution: {str(q['alternative_solution'])[:90]}")
            newline(9, 11)
        if q.get("common_traps"):
            c.setFont("Helvetica", 9)
            c.drawString(45, y, f"Common trap: {str(q['common_traps'])[:90]}")
            newline(9, 11)
        newline(10, 10)

    c.showPage()
    c.save()
    return buffer.getvalue()
