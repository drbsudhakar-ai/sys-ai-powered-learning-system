"""Shared validation and presentation helpers for administrator master data."""

from __future__ import annotations

from sqlalchemy import and_, case, func, inspect, or_
from sqlalchemy.orm import Session

from app import models, schemas, utils
from app.services import authentication as auth_service


def clean_optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def ensure_unique_email(
    db: Session,
    value: str | None,
    *,
    exclude_user_id: int | None = None,
) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = auth_service.normalize_email(str(value))
    query = db.query(models.User.id).filter(
        or_(
            func.lower(func.trim(models.User.email)) == normalized,
            func.lower(func.trim(models.User.institutional_email)) == normalized,
        )
    )
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if query.first():
        raise ValueError("Email already exists")
    return normalized


def ensure_unique_mobile(
    db: Session,
    value: str | None,
    *,
    exclude_user_id: int | None = None,
) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = auth_service.normalize_mobile(str(value))
    query = db.query(models.User.id).filter(
        or_(
            func.trim(models.User.mobile_number) == normalized,
            func.trim(models.User.institutional_mobile) == normalized,
        )
    )
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if query.first():
        raise ValueError("Mobile number already exists")
    return normalized


def record_audit(
    db: Session,
    actor: models.User,
    *,
    action: str,
    target_type: str,
    target_id: int | None,
    summary: str,
    changed_fields: list[str] | None = None,
) -> models.AdminAuditLog:
    row = models.AdminAuditLog(
        actor_user_id=actor.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary[:255],
        details={"changed_fields": sorted(set(changed_fields or []))},
    )
    db.add(row)
    return row


def mask_mobile(value: str | None) -> str | None:
    if not value:
        return None
    digits = str(value).strip()
    if len(digits) <= 4:
        return "••••"
    return f"••••••{digits[-4:]}"


def effective_registration_status(user: models.User) -> str:
    if not user.is_active or user.account_status == auth_service.ACCOUNT_DISABLED:
        return auth_service.ACCOUNT_DISABLED
    if user.account_status == auth_service.ACCOUNT_ACTIVE and utils.is_usable_password_hash(user.hashed_password):
        return auth_service.ACCOUNT_ACTIVE
    return auth_service.ACCOUNT_PENDING


def registered_account_predicate():
    return and_(models.User.is_active.is_(True), models.User.account_status == auth_service.ACCOUNT_ACTIVE, models.User.hashed_password.like("$2%"))


def pending_registration_predicate():
    return and_(models.User.is_active.is_(True), models.User.account_status != auth_service.ACCOUNT_DISABLED, or_(models.User.account_status != auth_service.ACCOUNT_ACTIVE, models.User.hashed_password.is_(None), ~models.User.hashed_password.like("$2%")))


def registration_status_predicate(value: str):
    if value == auth_service.ACCOUNT_ACTIVE:
        return registered_account_predicate()
    if value == auth_service.ACCOUNT_PENDING:
        return pending_registration_predicate()
    return or_(models.User.is_active.is_(False), models.User.account_status == auth_service.ACCOUNT_DISABLED)


def registration_status_expression():
    return case(
        (registered_account_predicate(), auth_service.ACCOUNT_ACTIVE),
        (or_(models.User.is_active.is_(False), models.User.account_status == auth_service.ACCOUNT_DISABLED), auth_service.ACCOUNT_DISABLED),
        else_=auth_service.ACCOUNT_PENDING,
    )


def master_record(db: Session, user: models.User) -> schemas.AdminMasterRecordOut:
    programmes: list[schemas.MasterProgrammeOut] = []
    coordinator_count = 0
    expert_count = 0
    if user.role == "student":
        rows = (
            db.query(models.Course.id, models.Course.title)
            .join(
                models.StudentCourseEnrollment,
                models.StudentCourseEnrollment.course_id == models.Course.id,
            )
            .filter(models.StudentCourseEnrollment.student_id == user.id)
            .order_by(models.Course.title, models.Course.id)
            .all()
        )
        programmes = [schemas.MasterProgrammeOut(id=row[0], title=row[1]) for row in rows]
    elif user.role == "faculty":
        coordinator_count = (
            db.query(models.FacultyCourseAssignment.id)
            .filter(models.FacultyCourseAssignment.faculty_id == user.id)
            .count()
        )
        expert_count = (
            db.query(models.SubjectExpertAssignment.id)
            .filter(models.SubjectExpertAssignment.faculty_id == user.id)
            .count()
        )

    # Administrator-maintained institutional contacts are canonical in master
    # views. Activated login contacts remain the fallback for older records.
    email = user.institutional_email or user.email
    mobile = user.institutional_mobile or user.mobile_number
    return schemas.AdminMasterRecordOut(
        id=user.id,
        role=user.role,
        name=user.name,
        photo_url=user.photo_url,
        roll_number=user.roll_number,
        employee_code=user.employee_code,
        email=email,
        email_verified=bool(user.email_verified),
        mobile_number=mobile,
        mobile_masked=mask_mobile(mobile),
        mobile_verified=bool(user.mobile_verified and user.mobile_is_personal),
        registration_status=effective_registration_status(user),
        is_active=bool(user.is_active),
        college=user.college,
        academic_program=user.academic_program,
        department=user.department,
        designation=user.designation,
        admission_year=user.admission_year,
        present_year=user.present_year,
        academic_status=user.academic_status,
        employment_status=user.employment_status,
        programmes=programmes,
        coordinator_assignments=coordinator_count,
        subject_expert_assignments=expert_count,
        last_login_at=None,
        last_login_available=False,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def master_profile(db: Session, user: models.User) -> schemas.AdminMasterProfileOut:
    coordinator_courses: list[schemas.MasterProgrammeOut] = []
    expert_subjects: list[schemas.MasterSubjectOut] = []
    if user.role == "faculty":
        course_rows = (
            db.query(models.Course.id, models.Course.title)
            .join(models.FacultyCourseAssignment, models.FacultyCourseAssignment.course_id == models.Course.id)
            .filter(models.FacultyCourseAssignment.faculty_id == user.id)
            .order_by(models.Course.title, models.Course.id)
            .all()
        )
        coordinator_courses = [schemas.MasterProgrammeOut(id=row[0], title=row[1]) for row in course_rows]
        subject_rows = (
            db.query(models.Subject.id, models.Subject.name)
            .join(models.SubjectExpertAssignment, models.SubjectExpertAssignment.subject_id == models.Subject.id)
            .filter(models.SubjectExpertAssignment.faculty_id == user.id)
            .order_by(models.Subject.name, models.Subject.id)
            .all()
        )
        expert_subjects = [schemas.MasterSubjectOut(id=row[0], name=row[1]) for row in subject_rows]
    return schemas.AdminMasterProfileOut(
        record=master_record(db, user),
        coordinator_courses=coordinator_courses,
        expert_subjects=expert_subjects,
        activity=_profile_activity(db, user, coordinator_courses),
    )


def _status_count(rows, statuses: set[str]) -> int:
    return sum(str(getattr(row, "status", "")).upper() in statuses for row in rows)


def _recent_date(row):
    return getattr(row, "created_at", None) or getattr(row, "generated_at", None)


def _profile_activity(db: Session, user: models.User, coordinator_courses) -> dict:
    """Read genuine module activity while supporting minimal test databases."""

    tables = set(inspect(db.get_bind()).get_table_names())

    def available(*names: str) -> bool:
        return all(name in tables for name in names)

    notifications = {"total": 0, "unread": 0, "recent": []}
    if available("notification_deliveries", "notifications"):
        deliveries = (
            db.query(models.NotificationDelivery, models.Notification)
            .join(models.Notification, models.Notification.id == models.NotificationDelivery.notification_id)
            .filter(models.NotificationDelivery.user_id == user.id)
            .order_by(models.NotificationDelivery.created_at.desc())
            .all()
        )
        notifications = {
            "total": len(deliveries),
            "unread": sum(not bool(delivery.is_read) for delivery, _ in deliveries),
            "recent": [{"title": notice.title or notice.subject or notice.event, "status": delivery.status} for delivery, notice in deliveries[:5]],
        }

    if user.role == "student":
        return _student_profile_activity(db, user, available, notifications)
    return _faculty_profile_activity(db, user, coordinator_courses, available, notifications)


def _student_profile_activity(db: Session, user: models.User, available, notifications: dict) -> dict:
    learning = {"total": 0, "completed": 0, "in_progress": 0, "recent": []}
    if available("learning_sessions", "learning_session_participants"):
        sessions = (
            db.query(models.LearningSession, models.LearningSessionParticipant)
            .join(models.LearningSessionParticipant, models.LearningSessionParticipant.session_id == models.LearningSession.id)
            .filter(models.LearningSessionParticipant.user_id == user.id, models.LearningSessionParticipant.status != "REMOVED")
            .order_by(models.LearningSession.created_at.desc())
            .all()
        )
        learning = {
            "total": len(sessions),
            "completed": sum(session.status == "COMPLETED" or participant.status == "COMPLETED" for session, participant in sessions),
            "in_progress": sum(session.status in {"IN_PROGRESS", "PAUSED"} for session, _ in sessions),
            "recent": [{"title": session.title, "mode": session.mode, "status": session.status} for session, _ in sessions[:5]],
        }

    assessments = {"attempted": 0, "completed": 0, "in_progress": 0, "average_percentage": None, "best_percentage": None, "recent": []}
    if available("assessment_attempts", "assessments"):
        attempts = (
            db.query(models.AssessmentAttempt, models.Assessment)
            .join(models.Assessment, models.Assessment.id == models.AssessmentAttempt.assessment_id)
            .filter(models.AssessmentAttempt.student_id == user.id)
            .order_by(models.AssessmentAttempt.id.desc())
            .all()
        )
        percentages = [float(attempt.percentage) for attempt, _ in attempts if attempt.percentage is not None]
        assessments = {
            "attempted": len(attempts),
            "completed": sum(str(attempt.status).upper() in {"SUBMITTED", "EVALUATED", "COMPLETED"} for attempt, _ in attempts),
            "in_progress": sum(str(attempt.status).upper() == "IN_PROGRESS" for attempt, _ in attempts),
            "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else None,
            "best_percentage": round(max(percentages), 1) if percentages else None,
            "recent": [{"title": assessment.title, "status": attempt.status, "percentage": attempt.percentage} for attempt, assessment in attempts[:5]],
        }

    performance = {"analyses": 0, "learning_gaps": 0, "high_priority_gaps": 0, "trend": None, "readiness": None, "areas": []}
    if available("performance_analyses"):
        analyses = db.query(models.PerformanceAnalysis).filter(models.PerformanceAnalysis.student_id == user.id).order_by(models.PerformanceAnalysis.generated_at.desc()).all()
        performance.update({"analyses": len(analyses), "trend": analyses[0].trend if analyses else None, "readiness": analyses[0].readiness_estimate if analyses else None})
    if available("learning_gaps"):
        gaps = db.query(models.LearningGap).filter(models.LearningGap.student_id == user.id).order_by(models.LearningGap.is_high_priority.desc(), models.LearningGap.id.desc()).all()
        performance.update({"learning_gaps": len(gaps), "high_priority_gaps": sum(bool(gap.is_high_priority) for gap in gaps), "areas": [{"name": gap.scope_name or gap.scope_type, "classification": gap.classification} for gap in gaps[:5]]})

    remediation = {"groups": 0, "interventions": 0, "active": 0, "completed": 0, "reassessments_pending": 0}
    group_ids = []
    if available("remedial_group_members", "remedial_groups"):
        memberships = db.query(models.RemedialGroupMember).filter(models.RemedialGroupMember.student_id == user.id).all()
        group_ids = [row.group_id for row in memberships]
        remediation["groups"] = len(group_ids)
    if available("remedial_interventions"):
        predicate = models.RemedialIntervention.student_id == user.id
        if group_ids:
            predicate = or_(predicate, models.RemedialIntervention.group_id.in_(group_ids))
        interventions = db.query(models.RemedialIntervention).filter(predicate).all()
        remediation.update({"interventions": len(interventions), "active": _status_count(interventions, {"ASSIGNED", "ACTIVE", "IN_PROGRESS"}), "completed": _status_count(interventions, {"COMPLETED"}), "reassessments_pending": sum(bool(row.reassessment_required) and not bool(row.reassessment_completed) for row in interventions)})

    mastery = {"topics": 0, "mastered": 0, "practice_needed": 0, "average_mastery": None, "practice_assigned": 0, "practice_completed": 0}
    if available("topic_mastery_states"):
        states = db.query(models.TopicMasteryState).filter(models.TopicMasteryState.student_id == user.id).all()
        percentages = [float(row.mastery_percent) for row in states if row.mastery_percent is not None]
        mastery.update({"topics": len(states), "mastered": _status_count(states, {"MASTERED"}), "practice_needed": _status_count(states, {"PRACTICE_REQUIRED", "NEEDS_PRACTICE", "REMEDIATION_REQUIRED"}), "average_mastery": round(sum(percentages) / len(percentages), 1) if percentages else None})
    if available("adaptive_practice_assignments"):
        assignments = db.query(models.AdaptivePracticeAssignment).filter(models.AdaptivePracticeAssignment.student_id == user.id).all()
        mastery.update({"practice_assigned": len(assignments), "practice_completed": _status_count(assignments, {"COMPLETED"})})

    journey = {"total_actions": 0, "pending_actions": 0, "completed_actions": 0, "next_action": None, "next_reason": None}
    if available("learning_journey_actions"):
        actions = db.query(models.LearningJourneyAction).filter(models.LearningJourneyAction.student_id == user.id).order_by(models.LearningJourneyAction.id.desc()).all()
        pending = [row for row in actions if str(row.status).upper() in {"RECOMMENDED", "PENDING", "IN_PROGRESS", "STARTED"}]
        journey.update({"total_actions": len(actions), "pending_actions": len(pending), "completed_actions": _status_count(actions, {"COMPLETED"}), "next_action": pending[0].title if pending else None, "next_reason": pending[0].reason if pending else None})

    support = {"high_priority_gaps": performance["high_priority_gaps"], "pending_remediation": remediation["active"], "pending_journey_actions": journey["pending_actions"], "unread_notifications": notifications["unread"]}
    return {"learning": learning, "assessments": assessments, "performance": performance, "remediation": remediation, "mastery": mastery, "journey": journey, "support": support, "notifications": notifications}


def _faculty_profile_activity(db: Session, user: models.User, coordinator_courses, available, notifications: dict) -> dict:
    teaching = {"total": 0, "completed": 0, "in_progress": 0, "recent": []}
    if available("learning_sessions"):
        sessions = db.query(models.LearningSession).filter(or_(models.LearningSession.created_by == user.id, models.LearningSession.facilitator_id == user.id)).order_by(models.LearningSession.created_at.desc()).all()
        teaching.update({"total": len(sessions), "completed": _status_count(sessions, {"COMPLETED"}), "in_progress": _status_count(sessions, {"IN_PROGRESS", "PAUSED"}), "recent": [{"title": row.title, "mode": row.mode, "status": row.status} for row in sessions[:5]]})

    assessments = {"created": 0, "published": 0, "draft": 0, "student_attempts": 0, "recent": []}
    if available("assessments"):
        created = db.query(models.Assessment).filter(models.Assessment.created_by == user.id).order_by(models.Assessment.created_at.desc()).all()
        assessments.update({"created": len(created), "published": _status_count(created, {"PUBLISHED", "ACTIVE"}), "draft": _status_count(created, {"DRAFT"}), "recent": [{"title": row.title, "status": row.status} for row in created[:5]]})
        if created and available("assessment_attempts"):
            assessments["student_attempts"] = db.query(models.AssessmentAttempt.id).filter(models.AssessmentAttempt.assessment_id.in_([row.id for row in created])).count()

    course_ids = [course.id for course in coordinator_courses]
    oversight = {"coordinator_courses": len(course_ids), "students": 0, "learning_gaps": 0, "high_priority_gaps": 0}
    if course_ids and available("student_course_enrollments"):
        oversight["students"] = db.query(func.count(func.distinct(models.StudentCourseEnrollment.student_id))).filter(models.StudentCourseEnrollment.course_id.in_(course_ids)).scalar() or 0
    if course_ids and available("learning_gaps"):
        gaps = db.query(models.LearningGap).filter(models.LearningGap.course_id.in_(course_ids)).all()
        oversight.update({"learning_gaps": len(gaps), "high_priority_gaps": sum(bool(row.is_high_priority) for row in gaps)})

    remediation = {"groups_created": 0, "interventions_created": 0, "active": 0, "completed": 0}
    if available("remedial_groups"):
        remediation["groups_created"] = db.query(models.RemedialGroup.id).filter(models.RemedialGroup.created_by == user.id).count()
    if available("remedial_interventions"):
        interventions = db.query(models.RemedialIntervention).filter(models.RemedialIntervention.created_by == user.id).all()
        remediation.update({"interventions_created": len(interventions), "active": _status_count(interventions, {"ASSIGNED", "ACTIVE", "IN_PROGRESS"}), "completed": _status_count(interventions, {"COMPLETED"})})

    content = {"questions_created": 0, "courses_created": 0}
    if available("questions"):
        content["questions_created"] = db.query(models.Question.id).filter(models.Question.created_by == user.id).count()
    if available("courses"):
        content["courses_created"] = db.query(models.Course.id).filter(models.Course.created_by == user.id).count()

    return {"teaching": teaching, "assessments": assessments, "oversight": oversight, "remediation": remediation, "content": content, "notifications": notifications}


def escaped_contains(column, value: str):
    escaped = value.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.lower(func.coalesce(column, "")).like(f"%{escaped}%", escape="\\")


def incomplete_master_predicate(role: str):
    contact_missing = and_(
        models.User.email.is_(None),
        models.User.institutional_email.is_(None),
        models.User.mobile_number.is_(None),
        models.User.institutional_mobile.is_(None),
    )
    identifier_missing = (
        or_(models.User.roll_number.is_(None), func.trim(models.User.roll_number) == "")
        if role == "student"
        else or_(models.User.employee_code.is_(None), func.trim(models.User.employee_code) == "")
    )
    return or_(contact_missing, identifier_missing, func.trim(models.User.name) == "")
