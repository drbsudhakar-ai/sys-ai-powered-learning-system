"""Student assessment attempt routes (P0-011)."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas, database
from app.academic_auth import is_admin, can_access_course_questions, is_course_coordinator
from app.routes.auth import get_current_user, require_roles
from app.services import attempt_engine as eng
from app.services import answer_key as ak
from app.services import notifications as notif_svc

router = APIRouter(tags=["Assessment Attempts"])
_staff = require_roles("admin", "faculty")


def _now():
    return datetime.now(timezone.utc)


@router.post("/courses/{course_id}/enroll", status_code=201)
def enroll_self(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if (current_user.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can self-enroll")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    eng.ensure_enrollment(db, current_user.id, course_id)
    return {"ok": True, "course_id": course_id}


@router.get("/student/assessments")
def list_student_assessments(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if (current_user.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    enrollments = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.student_id == current_user.id)
        .all()
    )
    course_ids = [e.course_id for e in enrollments]
    if course_id is not None:
        if course_id not in course_ids:
            raise HTTPException(status_code=403, detail="Not enrolled in course")
        course_ids = [course_id]
    if not course_ids:
        return {"available": [], "upcoming": [], "in_progress": [], "completed": []}

    assessments = (
        db.query(models.Assessment)
        .filter(models.Assessment.course_id.in_(course_ids), models.Assessment.status == "PUBLISHED")
        .all()
    )
    attempts = (
        db.query(models.AssessmentAttempt)
        .filter(models.AssessmentAttempt.student_id == current_user.id)
        .all()
    )
    by_assessment = {}
    for at in attempts:
        by_assessment.setdefault(at.assessment_id, []).append(at)

    available, upcoming, in_progress, completed = [], [], [], []
    now = _now()
    for a in assessments:
        version = eng.latest_published_version(db, a.id)
        open_ok, reason = eng.assessment_window_open(a, now)
        start = a.available_from
        ats = by_assessment.get(a.id, [])
        active = next((x for x in ats if x.status == "IN_PROGRESS"), None)
        if active:
            active = eng.maybe_auto_submit(db, active)
        done = [x for x in ats if x.status in ("SUBMITTED", "AUTO_SUBMITTED", "EVALUATED")]
        item = {
            "assessment_id": a.id,
            "title": a.title,
            "course_id": a.course_id,
            "assessment_type": a.assessment_type,
            "total_questions": a.total_questions,
            "total_marks": a.total_marks,
            "duration_minutes": a.duration_minutes,
            "available_from": a.available_from,
            "available_until": a.available_until or a.due_date,
            "max_attempts": a.max_attempts,
            "attempts_used": len(done) + (1 if active and active.status == "IN_PROGRESS" else 0),
            "version_id": version.id if version else None,
            "answer_key_available": eng.answer_key_is_released(a, now),
            "in_progress_attempt_id": active.id if active and active.status == "IN_PROGRESS" else None,
            "latest_result_attempt_id": done[-1].id if done else None,
            "latest_score": done[-1].total_marks_obtained if done else None,
            "latest_percentage": done[-1].percentage if done else None,
        }
        if active and active.status == "IN_PROGRESS":
            in_progress.append(item)
        elif done and (not open_ok or len(done) >= (a.max_attempts or 1)):
            completed.append(item)
        elif start and now < start:
            upcoming.append(item)
        elif open_ok:
            available.append(item)
        elif done:
            completed.append(item)
        else:
            upcoming.append({**item, "reason": reason})
    return {
        "available": available,
        "upcoming": upcoming,
        "in_progress": in_progress,
        "completed": completed,
    }


@router.get("/student/assessments/{assessment_id}/instructions")
def assessment_instructions(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    if (current_user.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not eng.is_student_enrolled(db, current_user.id, a.course_id):
        raise HTTPException(status_code=403, detail="Not enrolled")
    version = eng.latest_published_version(db, a.id)
    ok, reason = eng.assessment_window_open(a)
    return {
        "assessment_id": a.id,
        "title": a.title,
        "assessment_type": a.assessment_type,
        "duration_minutes": a.duration_minutes,
        "total_questions": a.total_questions,
        "total_marks": a.total_marks,
        "marks_correct": a.marks_correct,
        "marks_incorrect": a.marks_incorrect,
        "marks_unanswered": a.marks_unanswered,
        "max_attempts": a.max_attempts,
        "available": ok,
        "availability_message": reason,
        "version_id": version.id if version else None,
        "version_number": version.version_number if version else None,
    }


@router.post("/student/assessments/{assessment_id}/start", status_code=201)
def start_assessment(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = eng.start_attempt(db, current_user, assessment_id)
    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "version_id": attempt.version_id,
        "expires_at": attempt.expires_at,
        "remaining_seconds": eng.remaining_seconds(attempt),
        "attempt_number": attempt.attempt_number,
    }


@router.get("/student/attempts/{attempt_id}")
def get_attempt(
    attempt_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = eng.get_attempt_for_user(db, attempt_id, current_user, allow_staff=True)
    aqs = (
        db.query(models.AssessmentQuestion)
        .filter(models.AssessmentQuestion.version_id == attempt.version_id)
        .order_by(models.AssessmentQuestion.sequence)
        .all()
    )
    answers = {r.assessment_question_id: r for r in attempt.answer_responses}
    hide_answers = attempt.status == "IN_PROGRESS"
    questions = []
    for aq in aqs:
        ans = answers.get(aq.id)
        qpayload = {
            "assessment_question_id": aq.id,
            "sequence": aq.sequence,
            "stem": aq.stem_snapshot,
            "options": aq.options_snapshot or [],
            "difficulty": aq.difficulty,
            "marks": aq.marks_available,
            "subject": aq.subject_name_snapshot,
            "topic": aq.topic_name_snapshot,
            "selected_answer": ans.selected_answer if ans else None,
            "answered": bool(ans.answered) if ans else False,
            "marked_for_review": bool(ans.marked_for_review) if ans else False,
        }
        if not hide_answers and attempt.status == "EVALUATED":
            qpayload["correct_answer"] = aq.correct_answer_snapshot
            qpayload["explanation"] = aq.explanation_snapshot
        questions.append(qpayload)

    answered = sum(1 for q in questions if q["answered"])
    marked = sum(1 for q in questions if q["marked_for_review"])
    return {
        "attempt_id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "version_id": attempt.version_id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "expires_at": attempt.expires_at,
        "remaining_seconds": eng.remaining_seconds(attempt),
        "submitted_at": attempt.submitted_at,
        "summary": {
            "total": len(questions),
            "answered": answered,
            "unanswered": len(questions) - answered,
            "marked_review": marked,
        },
        "questions": questions,
    }


@router.post("/student/attempts/{attempt_id}/responses")
def save_attempt_response(
    attempt_id: int,
    payload: schemas.AttemptResponseIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = eng.get_attempt_for_user(db, attempt_id, current_user)
    if attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your attempt")
    row = eng.save_response(
        db,
        attempt,
        assessment_question_id=payload.assessment_question_id,
        selected_answer=payload.selected_answer,
        marked_for_review=payload.marked_for_review,
        clear=bool(payload.clear),
        time_spent_delta=payload.time_spent_delta or 0,
    )
    attempt = eng.get_attempt_for_user(db, attempt_id, current_user)
    return {
        "ok": True,
        "attempt_status": attempt.status,
        "remaining_seconds": eng.remaining_seconds(attempt),
        "response": {
            "assessment_question_id": row.assessment_question_id,
            "selected_answer": row.selected_answer,
            "answered": row.answered,
            "marked_for_review": row.marked_for_review,
        },
    }


@router.post("/student/attempts/{attempt_id}/submit")
def submit_attempt_route(
    attempt_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = eng.get_attempt_for_user(db, attempt_id, current_user)
    if attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your attempt")
    attempt = eng.submit_attempt(db, attempt, auto=False)
    try:
        notif_svc.create_notification(
            db,
            event="ASSESSMENT_COMPLETED",
            subject=f"Assessment completed by student {current_user.id}",
            body=f"Attempt {attempt.id} submitted for assessment {attempt.assessment_id}",
            assessment_id=attempt.assessment_id,
            course_id=attempt.course_id,
            student_id=current_user.id,
            dispatch=True,
        )
    except Exception:
        pass
    return eng.build_result_payload(db, attempt)


@router.get("/student/attempts/{attempt_id}/result")
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = eng.get_attempt_for_user(db, attempt_id, current_user, allow_staff=True)
    if attempt.status not in ("EVALUATED", "SUBMITTED", "AUTO_SUBMITTED"):
        raise HTTPException(status_code=400, detail="Result not available yet")
    if attempt.status != "EVALUATED":
        attempt = eng.evaluate_attempt(db, attempt)
    return eng.build_result_payload(db, attempt)


@router.post("/assessments/{assessment_id}/release-answer-key")
def release_answer_key(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(_staff),
):
    a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not is_admin(current_user) and not is_course_coordinator(db, current_user, a.course_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    a.answer_key_released = True
    db.commit()
    try:
        notif_svc.create_notification(
            db,
            event="ANSWER_KEY_AVAILABLE",
            subject=f"Answer key available: {a.title}",
            body=f"Answer key released for assessment {a.id}",
            assessment_id=a.id,
            course_id=a.course_id,
            dispatch=True,
        )
    except Exception:
        pass
    return {"ok": True, "assessment_id": a.id, "answer_key_released": True}


def _can_view_answer_key(db: Session, user: models.User, assessment: models.Assessment) -> bool:
    role = (user.role or "").lower()
    if not eng.answer_key_is_released(assessment):
        return False
    # hide while this student has an active attempt
    if role == "student":
        active = (
            db.query(models.AssessmentAttempt)
            .filter(
                models.AssessmentAttempt.student_id == user.id,
                models.AssessmentAttempt.assessment_id == assessment.id,
                models.AssessmentAttempt.status == "IN_PROGRESS",
            )
            .first()
        )
        if active:
            return False
        return eng.is_student_enrolled(db, user.id, assessment.course_id)
    return can_access_course_questions(db, user, assessment.course_id) or is_admin(user)


@router.get("/assessments/{assessment_id}/answer-key")
def get_answer_key_json(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not _can_view_answer_key(db, current_user, a):
        raise HTTPException(status_code=403, detail="Answer key is not available")
    version = eng.latest_published_version(db, a.id)
    if not version:
        raise HTTPException(status_code=404, detail="No published version")
    return ak.build_answer_key_payload(db, version)


@router.get("/assessments/{assessment_id}/answer-key.pdf")
def download_answer_key_pdf(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    a = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not _can_view_answer_key(db, current_user, a):
        raise HTTPException(status_code=403, detail="Answer key is not available")
    version = eng.latest_published_version(db, a.id)
    if not version:
        raise HTTPException(status_code=404, detail="No published version")
    payload = ak.build_answer_key_payload(db, version)
    pdf = ak.render_answer_key_pdf(payload)
    filename = f"sys_answer_key_a{assessment_id}_v{version.version_number}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/assessment-versions/{version_id}/answer-key.pdf")
def download_version_answer_key_pdf(
    version_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    version = db.query(models.AssessmentVersion).filter(models.AssessmentVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    a = db.query(models.Assessment).filter(models.Assessment.id == version.assessment_id).first()
    if not a or not _can_view_answer_key(db, current_user, a):
        raise HTTPException(status_code=403, detail="Answer key is not available")
    payload = ak.build_answer_key_payload(db, version)
    pdf = ak.render_answer_key_pdf(payload)
    filename = f"sys_answer_key_v{version.version_number}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
