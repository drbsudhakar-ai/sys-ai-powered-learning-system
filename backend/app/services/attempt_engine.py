"""Student assessment attempt lifecycle + server-side evaluation (P0-011)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, roles
from app.services import notifications as notif_svc


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _norm(ans: Optional[str]) -> str:
    return " ".join((ans or "").strip().lower().split())


def is_student_enrolled(db: Session, student_id: int, course_id: int) -> bool:
    return (
        db.query(models.StudentCourseEnrollment)
        .filter(
            models.StudentCourseEnrollment.student_id == student_id,
            models.StudentCourseEnrollment.course_id == course_id,
        )
        .first()
        is not None
    )


def ensure_enrollment(db: Session, student_id: int, course_id: int) -> None:
    if not is_student_enrolled(db, student_id, course_id):
        db.add(models.StudentCourseEnrollment(student_id=student_id, course_id=course_id))
        db.commit()


def latest_published_version(db: Session, assessment_id: int) -> Optional[models.AssessmentVersion]:
    return (
        db.query(models.AssessmentVersion)
        .filter(models.AssessmentVersion.assessment_id == assessment_id)
        .order_by(models.AssessmentVersion.version_number.desc())
        .first()
    )


def assessment_window_open(assessment: models.Assessment, now: Optional[datetime] = None) -> Tuple[bool, str]:
    now = now or _utcnow()
    if assessment.status != "PUBLISHED":
        return False, "Assessment is not published"
    start = _aware(assessment.available_from)
    end = _aware(assessment.available_until or assessment.due_date)
    if start and now < start:
        return False, "Assessment is not yet available"
    if end and now > end:
        return False, "Assessment availability window has ended"
    return True, "ok"


def answer_key_is_released(assessment: models.Assessment, now: Optional[datetime] = None) -> bool:
    now = now or _utcnow()
    if assessment.answer_key_released:
        return True
    end = _aware(assessment.available_until or assessment.due_date)
    if end and now > end:
        return True
    return False


def snapshot_question_onto_aq(
    db: Session,
    aq: models.AssessmentQuestion,
    q: models.Question,
    marks_each: float,
    neg_marks: float,
) -> None:
    subject = db.query(models.Subject).filter(models.Subject.id == q.subject_id).first() if q.subject_id else None
    topic = db.query(models.Topic).filter(models.Topic.id == q.topic_id).first() if q.topic_id else None
    aq.stem_snapshot = q.stem
    aq.options_snapshot = q.options
    aq.correct_answer_snapshot = q.correct_answer
    aq.explanation_snapshot = q.explanation
    aq.question_type_snapshot = q.question_type
    aq.shortcut_snapshot = q.shortcut
    aq.alternative_solution_snapshot = q.alternative_solution
    aq.common_traps_snapshot = q.common_traps
    aq.negative_marks_snapshot = q.negative_marks if q.negative_marks is not None else neg_marks
    aq.marks_available = q.marks if q.marks is not None else marks_each
    aq.subject_name_snapshot = subject.name if subject else None
    aq.topic_name_snapshot = topic.name if topic else None
    aq.subject_id = q.subject_id
    aq.topic_id = q.topic_id
    aq.subtopic_id = q.subtopic_id
    aq.difficulty = q.difficulty


def remaining_seconds(attempt: models.AssessmentAttempt, now: Optional[datetime] = None) -> int:
    now = now or _utcnow()
    if attempt.status not in ("IN_PROGRESS",):
        return 0
    if not attempt.expires_at:
        return 0
    exp = attempt.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return max(0, int((exp - now).total_seconds()))


def maybe_auto_submit(db: Session, attempt: models.AssessmentAttempt) -> models.AssessmentAttempt:
    if attempt.status != "IN_PROGRESS":
        return attempt
    if remaining_seconds(attempt) > 0:
        return attempt
    return submit_attempt(db, attempt, auto=True)


def start_attempt(db: Session, student: models.User, assessment_id: int) -> models.AssessmentAttempt:
    if (student.role or "").lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can start assessment attempts")
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    ok, reason = assessment_window_open(assessment)
    if not ok:
        raise HTTPException(status_code=403, detail=reason)
    if not is_student_enrolled(db, student.id, assessment.course_id):
        raise HTTPException(status_code=403, detail="Student is not enrolled in this course")

    # Resume in-progress (auto-submit if expired, then allow new attempt if under limit)
    existing = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.student_id == student.id,
            models.AssessmentAttempt.assessment_id == assessment_id,
            models.AssessmentAttempt.status == "IN_PROGRESS",
        )
        .first()
    )
    if existing:
        existing = maybe_auto_submit(db, existing)
        if existing.status == "IN_PROGRESS":
            return existing

    prior_count = (
        db.query(models.AssessmentAttempt)
        .filter(
            models.AssessmentAttempt.student_id == student.id,
            models.AssessmentAttempt.assessment_id == assessment_id,
            models.AssessmentAttempt.status.in_(("SUBMITTED", "AUTO_SUBMITTED", "EVALUATED")),
        )
        .count()
    )
    max_attempts = assessment.max_attempts or 1
    if prior_count >= max_attempts:
        raise HTTPException(status_code=403, detail="Attempt limit reached")

    version = latest_published_version(db, assessment_id)
    if not version:
        raise HTTPException(status_code=400, detail="Assessment has no published version")

    now = _utcnow()
    duration = version.duration_minutes or assessment.duration_minutes or 60
    attempt = models.AssessmentAttempt(
        student_id=student.id,
        assessment_id=assessment.id,
        version_id=version.id,
        course_id=assessment.course_id,
        attempt_number=prior_count + 1,
        status="IN_PROGRESS",
        started_at=now,
        expires_at=now + timedelta(minutes=duration),
        auto_submitted=False,
        total_marks_available=version.total_marks or assessment.total_marks,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def get_attempt_for_user(
    db: Session,
    attempt_id: int,
    user: models.User,
    *,
    allow_staff: bool = False,
) -> models.AssessmentAttempt:
    attempt = (
        db.query(models.AssessmentAttempt)
        .options(
            joinedload(models.AssessmentAttempt.answer_responses),
            joinedload(models.AssessmentAttempt.assessment),
            joinedload(models.AssessmentAttempt.version),
        )
        .filter(models.AssessmentAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    role = (user.role or "").lower()
    if attempt.student_id == user.id:
        return maybe_auto_submit(db, attempt) if attempt.status == "IN_PROGRESS" else attempt
    if allow_staff and (roles.is_admin_role(role) or role == roles.FACULTY):
        return attempt
    raise HTTPException(status_code=403, detail="Not allowed to access this attempt")


def save_response(
    db: Session,
    attempt: models.AssessmentAttempt,
    *,
    assessment_question_id: int,
    selected_answer: Optional[str] = None,
    marked_for_review: Optional[bool] = None,
    clear: bool = False,
    time_spent_delta: float = 0,
) -> models.AttemptResponse:
    attempt = maybe_auto_submit(db, attempt)
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Attempt is no longer editable")

    aq = (
        db.query(models.AssessmentQuestion)
        .filter(
            models.AssessmentQuestion.id == assessment_question_id,
            models.AssessmentQuestion.version_id == attempt.version_id,
        )
        .first()
    )
    if not aq:
        raise HTTPException(status_code=404, detail="Question not in this assessment version")

    row = (
        db.query(models.AttemptResponse)
        .filter(
            models.AttemptResponse.attempt_id == attempt.id,
            models.AttemptResponse.assessment_question_id == assessment_question_id,
        )
        .first()
    )
    if not row:
        row = models.AttemptResponse(
            attempt_id=attempt.id,
            assessment_question_id=assessment_question_id,
            question_id=aq.question_id,
            question_sequence=aq.sequence,
        )
        db.add(row)

    if clear:
        row.selected_answer = None
        row.answered = False
        row.submitted_answer_snapshot = None
    elif selected_answer is not None:
        row.selected_answer = selected_answer
        row.answered = bool(str(selected_answer).strip())
        row.submitted_answer_snapshot = selected_answer
    if marked_for_review is not None:
        row.marked_for_review = bool(marked_for_review)
    row.time_spent_seconds = float(row.time_spent_seconds or 0) + max(0.0, float(time_spent_delta or 0))
    db.commit()
    db.refresh(row)
    return row


def evaluate_attempt(db: Session, attempt: models.AssessmentAttempt) -> models.AssessmentAttempt:
    assessment = attempt.assessment or db.query(models.Assessment).get(attempt.assessment_id)
    version = attempt.version or db.query(models.AssessmentVersion).get(attempt.version_id)
    marking = (version.marking_snapshot if version else None) or {}
    marks_correct = float(
        marking.get("marks_correct", assessment.marks_correct if assessment else 1) or 1
    )
    marks_incorrect = float(
        marking.get("marks_incorrect", assessment.marks_incorrect if assessment else 0) or 0
    )
    marks_unanswered = float(
        marking.get("marks_unanswered", assessment.marks_unanswered if assessment else 0) or 0
    )

    aqs = (
        db.query(models.AssessmentQuestion)
        .filter(models.AssessmentQuestion.version_id == attempt.version_id)
        .order_by(models.AssessmentQuestion.sequence)
        .all()
    )
    answers = {
        r.assessment_question_id: r
        for r in db.query(models.AttemptResponse)
        .filter(models.AttemptResponse.attempt_id == attempt.id)
        .all()
    }

    # Clear prior performance records for re-eval safety
    db.query(models.PerformanceRecord).filter(models.PerformanceRecord.attempt_id == attempt.id).delete()

    obtained = 0.0
    available = 0.0
    correct = incorrect = unanswered = 0

    for aq in aqs:
        ans = answers.get(aq.id)
        selected = ans.selected_answer if ans and ans.answered else None
        q_marks = float(aq.marks_available or marks_correct)
        neg = float(
            aq.negative_marks_snapshot if aq.negative_marks_snapshot is not None else marks_incorrect
        )
        available += q_marks
        is_correct = is_incorrect = is_unanswered = False
        marks_got = 0.0
        neg_applied = 0.0

        if selected is None or not str(selected).strip():
            is_unanswered = True
            unanswered += 1
            marks_got = marks_unanswered
        elif _norm(selected) == _norm(aq.correct_answer_snapshot):
            is_correct = True
            correct += 1
            marks_got = q_marks
        else:
            is_incorrect = True
            incorrect += 1
            marks_got = neg
            neg_applied = abs(min(neg, 0))

        obtained += marks_got
        db.add(
            models.PerformanceRecord(
                attempt_id=attempt.id,
                student_id=attempt.student_id,
                course_id=attempt.course_id,
                assessment_id=attempt.assessment_id,
                assessment_version_id=attempt.version_id,
                assessment_category=assessment.category if assessment else None,
                assessment_type=assessment.assessment_type if assessment else None,
                assessment_date=attempt.submitted_at or _utcnow(),
                subject_id=aq.subject_id,
                topic_id=aq.topic_id,
                subtopic_id=aq.subtopic_id,
                question_id=aq.question_id,
                question_type=aq.question_type_snapshot,
                difficulty=aq.difficulty,
                marks_available=q_marks,
                marks_obtained=marks_got,
                is_correct=is_correct,
                is_incorrect=is_incorrect,
                is_unanswered=is_unanswered,
                response_time_seconds=float(ans.time_spent_seconds) if ans else None,
                negative_marks=neg_applied,
                attempt_number=attempt.attempt_number,
            )
        )

    attempt.total_marks_obtained = round(obtained, 4)
    attempt.total_marks_available = round(available, 4)
    attempt.percentage = round(100.0 * obtained / available, 2) if available else 0.0
    attempt.correct_count = correct
    attempt.incorrect_count = incorrect
    attempt.unanswered_count = unanswered
    if attempt.started_at and attempt.submitted_at:
        start = attempt.started_at
        end = attempt.submitted_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        attempt.time_spent_seconds = max(0.0, (end - start).total_seconds())
    attempt.status = "EVALUATED"
    db.commit()
    db.refresh(attempt)

    try:
        notif_svc.create_notification(
            db,
            event="ASSESSMENT_EVALUATED",
            subject=f"Assessment evaluated: {assessment.title if assessment else attempt.assessment_id}",
            body=(
                f"Student {attempt.student_id} scored {attempt.total_marks_obtained}/"
                f"{attempt.total_marks_available} ({attempt.percentage}%)"
            ),
            assessment_id=attempt.assessment_id,
            course_id=attempt.course_id,
            student_id=attempt.student_id,
            dispatch=True,
        )
    except Exception:
        pass
    try:
        from app.services.performance_analyzer import run_post_evaluation_pipeline

        run_post_evaluation_pipeline(db, attempt)
    except Exception:
        pass
    return attempt


def submit_attempt(
    db: Session,
    attempt: models.AssessmentAttempt,
    *,
    auto: bool = False,
) -> models.AssessmentAttempt:
    if attempt.status in ("SUBMITTED", "AUTO_SUBMITTED", "EVALUATED"):
        return attempt
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Attempt cannot be submitted")
    now = _utcnow()
    attempt.submitted_at = now
    attempt.auto_submitted = bool(auto)
    attempt.status = "AUTO_SUBMITTED" if auto else "SUBMITTED"
    db.commit()
    db.refresh(attempt)
    return evaluate_attempt(db, attempt)


def build_result_payload(db: Session, attempt: models.AssessmentAttempt) -> Dict[str, Any]:
    records = (
        db.query(models.PerformanceRecord)
        .filter(models.PerformanceRecord.attempt_id == attempt.id)
        .all()
    )
    by_subject: Dict[int, Dict[str, float]] = {}
    by_topic: Dict[int, Dict[str, float]] = {}
    by_diff: Dict[str, Dict[str, float]] = {}

    def _acc(bucket: Dict, key, rec: models.PerformanceRecord):
        if key is None:
            return
        if key not in bucket:
            bucket[key] = {
                "attempted": 0,
                "correct": 0,
                "incorrect": 0,
                "unanswered": 0,
                "marks_obtained": 0.0,
                "marks_available": 0.0,
            }
        b = bucket[key]
        b["marks_obtained"] += float(rec.marks_obtained or 0)
        b["marks_available"] += float(rec.marks_available or 0)
        if rec.is_unanswered:
            b["unanswered"] += 1
        else:
            b["attempted"] += 1
            if rec.is_correct:
                b["correct"] += 1
            if rec.is_incorrect:
                b["incorrect"] += 1

    for r in records:
        _acc(by_subject, r.subject_id, r)
        _acc(by_topic, r.topic_id, r)
        _acc(by_diff, r.difficulty, r)

    def _finalize(raw: Dict, name_fn) -> List[Dict[str, Any]]:
        out = []
        for key, vals in raw.items():
            avail = vals["marks_available"] or 0
            attempted = vals["attempted"]
            correct = vals["correct"]
            out.append(
                {
                    "id": key,
                    "name": name_fn(key),
                    **vals,
                    "percentage": round(100.0 * vals["marks_obtained"] / avail, 2) if avail else None,
                    "accuracy": round(100.0 * correct / attempted, 2) if attempted else None,
                }
            )
        return out

    subjects = {s.id: s.name for s in db.query(models.Subject).all()}
    topics = {t.id: t.name for t in db.query(models.Topic).all()}

    assessment = attempt.assessment
    return {
        "attempt_id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "version_id": attempt.version_id,
        "status": attempt.status,
        "auto_submitted": attempt.auto_submitted,
        "score": attempt.total_marks_obtained,
        "total_marks": attempt.total_marks_available,
        "percentage": attempt.percentage,
        "correct": attempt.correct_count,
        "incorrect": attempt.incorrect_count,
        "unanswered": attempt.unanswered_count,
        "attempted": (attempt.correct_count or 0) + (attempt.incorrect_count or 0),
        "accuracy": (
            round(
                100.0
                * (attempt.correct_count or 0)
                / max((attempt.correct_count or 0) + (attempt.incorrect_count or 0), 1),
                2,
            )
            if (attempt.correct_count or 0) + (attempt.incorrect_count or 0)
            else None
        ),
        "time_spent_seconds": attempt.time_spent_seconds,
        "submitted_at": attempt.submitted_at,
        "assessment_title": assessment.title if assessment else None,
        "assessment_type": assessment.assessment_type if assessment else None,
        "subject_performance": _finalize(by_subject, lambda i: subjects.get(i, str(i))),
        "topic_performance": _finalize(by_topic, lambda i: topics.get(i, str(i))),
        "difficulty_performance": _finalize(by_diff, lambda i: i),
    }
