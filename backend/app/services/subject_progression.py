"""P0-019 Student-controlled subject selection, in-subject topic progression, course balance.

Does not impose a subject order. Does not recalculate mastery, gaps, or assessments.
Does not invent prerequisite edges — only uses topic_prerequisites rows when present.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.academic_auth import can_access_course_questions, is_admin
from app.constants import (
    DEFAULT_BALANCE_ATTENTION_POINTS,
    DEFAULT_BALANCE_LEAD_COVERAGE,
    DEFAULT_BALANCE_LEAD_MASTERED,
    DEFAULT_BALANCE_URGENT_POINTS,
    DEFAULT_BALANCE_WATCH_POINTS,
)
from app.services import notifications as notif_svc

SUPPORT_STATUSES = ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED")
ACTIVE_GAP_CLASS = ("WEAK", "CRITICAL_GAP", "DEVELOPING")
STATUS_RANK = {
    "REASSESSMENT_PENDING": 0,
    "READY_FOR_REASSESSMENT": 1,
    "NEEDS_REMEDIATION": 2,
    "MASTERY_REGRESSED": 3,
    "REMEDIATION_IN_PROGRESS": 4,
    "NEEDS_PRACTICE": 5,
    "LEARNING": 6,
    "NOT_ASSESSED": 7,
    "MASTERED": 90,
}


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _authorize_student_view(db: Session, actor: models.User, student_id: int, course_id: int) -> None:
    if not notif_svc.user_can_view_student_performance(db, actor, student_id, course_id):
        raise _http(403, "Not authorized for this student/course")


def _authorize_faculty_course(db: Session, actor: models.User, course_id: int) -> None:
    role = (actor.role or "").lower()
    if role == "student":
        raise _http(403, "Faculty or admin access required")
    if is_admin(actor):
        return
    if can_access_course_questions(db, actor, course_id):
        return
    raise _http(403, "Not authorized for this course")


def _require_enrollment(db: Session, student_id: int, course_id: int) -> None:
    enr = (
        db.query(models.StudentCourseEnrollment)
        .filter(
            models.StudentCourseEnrollment.student_id == student_id,
            models.StudentCourseEnrollment.course_id == course_id,
        )
        .first()
    )
    if not enr:
        raise _http(403, "Not enrolled in this course")


def _gap_resolved(gap: models.LearningGap) -> bool:
    return str((gap.inference or {}).get("mastery_status") or "").upper() == "RESOLVED"


def _course_subjects(db: Session, course_id: int) -> List[models.Subject]:
    return (
        db.query(models.Subject)
        .filter(models.Subject.course_id == course_id)
        .order_by(models.Subject.id)
        .all()
    )


def _subject_topics(db: Session, subject_id: int) -> List[models.Topic]:
    return (
        db.query(models.Topic)
        .filter(models.Topic.subject_id == subject_id)
        .order_by(models.Topic.id)
        .all()
    )


def _prereq_map(db: Session, topic_ids: List[int]) -> Dict[int, List[int]]:
    if not topic_ids:
        return {}
    rows = (
        db.query(models.TopicPrerequisite)
        .filter(models.TopicPrerequisite.topic_id.in_(topic_ids))
        .all()
    )
    out: Dict[int, List[int]] = {}
    for r in rows:
        out.setdefault(r.topic_id, []).append(r.prerequisite_topic_id)
    return out


def _sufficient_mastery(status: Optional[str]) -> bool:
    return (status or "") == "MASTERED"


def list_course_subjects(db: Session, actor: models.User, *, student_id: int, course_id: int) -> Dict[str, Any]:
    _authorize_student_view(db, actor, student_id, course_id)
    if (actor.role or "").lower() == "student":
        _require_enrollment(db, student_id, course_id)
    subjects = _course_subjects(db, course_id)
    return {
        "course_id": course_id,
        "student_id": student_id,
        "subject_order_imposed": False,
        "note": "You may begin any enrolled subject at any time. SYS does not rank subjects as a required sequence.",
        "subjects": [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in subjects
        ],
    }


def focus_subject(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    subject_id: int,
) -> models.StudentSubjectFocus:
    _authorize_student_view(db, actor, student_id, course_id)
    if (actor.role or "").lower() == "student" and actor.id != student_id:
        raise _http(403, "Students may only change their own subject focus")
    if (actor.role or "").lower() == "student":
        _require_enrollment(db, student_id, course_id)
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject or subject.course_id != course_id:
        raise _http(404, "Subject is not part of this course")
    row = (
        db.query(models.StudentSubjectFocus)
        .filter(
            models.StudentSubjectFocus.student_id == student_id,
            models.StudentSubjectFocus.course_id == course_id,
            models.StudentSubjectFocus.subject_id == subject_id,
        )
        .first()
    )
    now = _utcnow()
    if not row:
        row = models.StudentSubjectFocus(
            student_id=student_id,
            course_id=course_id,
            subject_id=subject_id,
            last_focused_at=now,
        )
        db.add(row)
    else:
        row.last_focused_at = now
    db.commit()
    db.refresh(row)
    return row


def last_focused_subject_id(db: Session, *, student_id: int, course_id: int) -> Optional[int]:
    row = (
        db.query(models.StudentSubjectFocus)
        .filter(
            models.StudentSubjectFocus.student_id == student_id,
            models.StudentSubjectFocus.course_id == course_id,
        )
        .order_by(models.StudentSubjectFocus.last_focused_at.desc())
        .first()
    )
    return row.subject_id if row else None


def _intel_score(db: Session, course_id: int, topic_id: int) -> float:
    snap = (
        db.query(models.TopicIntelligenceSnapshot)
        .filter(
            models.TopicIntelligenceSnapshot.course_id == course_id,
            models.TopicIntelligenceSnapshot.topic_id == topic_id,
        )
        .first()
    )
    if snap and snap.priority_score is not None:
        return float(snap.priority_score)
    tw = (
        db.query(models.TopicWeightage)
        .filter(models.TopicWeightage.topic_id == topic_id)
        .first()
    )
    if tw and tw.weight_percent is not None:
        return float(tw.weight_percent) / 100.0
    return 0.0


def _prereq_warning(
    topic: models.Topic,
    prereq_ids: List[int],
    topics_by_id: Dict[int, models.Topic],
    states: Dict[int, models.TopicMasteryState],
) -> Optional[Dict[str, Any]]:
    if not prereq_ids:
        return {
            "has_authoritative_prerequisites": False,
            "blocking": False,
            "message": "SYS cannot establish a prerequisite confidently for this topic — no authoritative prerequisite metadata is recorded. You may continue.",
            "deficient": [],
        }
    deficient = []
    for pid in prereq_ids:
        st = states.get(pid)
        status = st.status if st else "NOT_ASSESSED"
        if not _sufficient_mastery(status):
            pt = topics_by_id.get(pid)
            deficient.append(
                {
                    "topic_id": pid,
                    "topic_name": pt.name if pt else f"Topic {pid}",
                    "mastery_status": status,
                }
            )
    if not deficient:
        return {
            "has_authoritative_prerequisites": True,
            "blocking": False,
            "satisfied": True,
            "message": "Recorded prerequisites appear sufficiently mastered.",
            "deficient": [],
        }
    names = ", ".join(d["topic_name"] for d in deficient)
    return {
        "has_authoritative_prerequisites": True,
        "blocking": False,
        "satisfied": False,
        "message": (
            f"You can continue to {topic.name}, but {names} "
            f"{'is' if len(deficient) == 1 else 'are'} an important prerequisite and current mastery is insufficient. "
            "We recommend reviewing the prerequisite first."
        ),
        "deficient": deficient,
        "options": [
            {"action": "LEARN_PREREQUISITE", "label": "Learn prerequisite first"},
            {"action": "PREREQUISITE_CHECK", "label": "Take quick prerequisite check", "href": "/mastery/me"},
            {"action": "CONTINUE_SELECTED", "label": "Continue to selected topic"},
        ],
    }


def recommend_topic_in_subject(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    subject_id: int,
) -> Dict[str, Any]:
    topics = _subject_topics(db, subject_id)
    topics_by_id = {t.id: t for t in topics}
    ids = [t.id for t in topics]
    states_rows = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
            models.TopicMasteryState.topic_id.in_(ids or [-1]),
        )
        .all()
    )
    states = {s.topic_id: s for s in states_rows}
    prereqs = _prereq_map(db, ids)
    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
            models.LearningGap.scope_type == "TOPIC",
            models.LearningGap.scope_id.in_(ids or [-1]),
        )
        .all()
    )
    gap_topics = {g.scope_id for g in gaps if not _gap_resolved(g) and g.classification in ACTIVE_GAP_CLASS}

    def sort_key(topic: models.Topic) -> Tuple:
        st = states.get(topic.id)
        status = st.status if st else "NOT_ASSESSED"
        prereq_ids = prereqs.get(topic.id) or []
        unsatisfied = any(
            not _sufficient_mastery(states.get(p).status if states.get(p) else "NOT_ASSESSED")
            for p in prereq_ids
        )
        # Prefer satisfied prereqs; then need-based status; then syllabus order (id); intelligence as last tiebreak (negated)
        return (
            1 if status == "MASTERED" else 0,
            1 if unsatisfied else 0,
            STATUS_RANK.get(status, 50),
            0 if topic.id in gap_topics else 1,
            topic.id,
            -_intel_score(db, course_id, topic.id),
        )

    ordered = sorted(topics, key=sort_key)
    primary = next((t for t in ordered if (states.get(t.id).status if states.get(t.id) else "NOT_ASSESSED") != "MASTERED"), None)
    if primary is None and topics:
        # All mastered — recommend review of last syllabus topic
        primary = topics[-1]
        all_mastered = True
    else:
        all_mastered = False

    def topic_row(t: models.Topic) -> Dict[str, Any]:
        st = states.get(t.id)
        status = st.status if st else "NOT_ASSESSED"
        return {
            "topic_id": t.id,
            "topic_name": t.name,
            "mastery_status": status,
            "indicator": st.indicator if st else "GRAY",
            "mastered": status == "MASTERED",
            "source_of_truth": "P0-015_TopicMasteryState" if st else "curriculum",
            "prerequisites": [
                {
                    "topic_id": pid,
                    "topic_name": topics_by_id[pid].name if pid in topics_by_id else f"Topic {pid}",
                    "mastered": _sufficient_mastery(states.get(pid).status if states.get(pid) else None),
                }
                for pid in (prereqs.get(t.id) or [])
            ],
        }

    warning = None
    reason = "No topics are defined for this subject yet."
    if primary:
        warning = _prereq_warning(primary, prereqs.get(primary.id) or [], topics_by_id, states)
        st = states.get(primary.id)
        status = st.status if st else "NOT_ASSESSED"
        if all_mastered:
            reason = (
                f"{primary.name} is suggested for review because every topic in this subject is mastered (P0-015)."
            )
        elif status in SUPPORT_STATUSES:
            reason = (
                f"{primary.name} is recommended because P0-015 status is {status.replace('_', ' ').title()}."
            )
        elif status == "READY_FOR_REASSESSMENT":
            reason = f"{primary.name} is recommended because you are ready for reassessment (P0-015)."
        elif status == "NEEDS_PRACTICE":
            reason = f"{primary.name} is recommended because practice evidence is still required (P0-015)."
        else:
            prev = None
            idx = next((i for i, t in enumerate(topics) if t.id == primary.id), 0)
            if idx > 0:
                prev = topics[idx - 1]
            if prev and _sufficient_mastery(states.get(prev.id).status if states.get(prev.id) else None):
                reason = (
                    f"{primary.name} is recommended because {prev.name} is mastered and "
                    f"{primary.name} is the next prerequisite-supported topic in your learning path."
                )
            elif warning and warning.get("has_authoritative_prerequisites") and not warning.get("satisfied"):
                reason = warning["message"]
            else:
                reason = (
                    f"{primary.name} is recommended as the next unmastered topic in this subject "
                    f"(syllabus order by recorded topic sequence)."
                )
            if primary.id in gap_topics:
                reason += " An active P0-012 learning gap is also recorded for this topic."

    alts = []
    for t in ordered:
        if primary and t.id == primary.id:
            continue
        if (states.get(t.id).status if states.get(t.id) else "NOT_ASSESSED") == "MASTERED":
            continue
        alts.append(topic_row(t))
        if len(alts) >= 5:
            break

    return {
        "subject_id": subject_id,
        "course_id": course_id,
        "student_id": student_id,
        "recommended": topic_row(primary) if primary else None,
        "reason": reason,
        "prerequisite_warning": warning if primary else None,
        "alternatives": alts,
        "topics": [topic_row(t) for t in topics],
        "subject_order_imposed": False,
        "authority_note": "Topic mastery comes from P0-015. Prerequisites are used only when recorded in topic_prerequisites.",
    }


def choose_topic(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    subject_id: int,
    topic_id: int,
) -> Dict[str, Any]:
    """Student override: selected topic becomes the teaching target. Advisory prereq warning only."""
    _authorize_student_view(db, actor, student_id, course_id)
    if (actor.role or "").lower() == "student":
        if actor.id != student_id:
            raise _http(403, "Students may only choose their own topics")
        _require_enrollment(db, student_id, course_id)
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic or topic.subject_id != subject_id:
        raise _http(422, "Topic does not belong to the selected subject")
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject or subject.course_id != course_id:
        raise _http(404, "Subject is not part of this course")
    row = focus_subject(db, actor, student_id=student_id, course_id=course_id, subject_id=subject_id)
    row.selected_topic_id = topic_id
    db.commit()
    rec = recommend_topic_in_subject(db, student_id=student_id, course_id=course_id, subject_id=subject_id)
    topics_by_id = {t.id: t for t in _subject_topics(db, subject_id)}
    states = {
        s.topic_id: s
        for s in db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
            models.TopicMasteryState.topic_id.in_(list(topics_by_id) or [-1]),
        )
        .all()
    }
    prereqs = _prereq_map(db, [topic_id])
    warning = _prereq_warning(topic, prereqs.get(topic_id) or [], topics_by_id, states)
    return {
        "override": True,
        "teaching_target": {
            "subject_id": subject_id,
            "subject_name": subject.name,
            "topic_id": topic.id,
            "topic_name": topic.name,
        },
        "recommended": rec.get("recommended"),
        "chose_recommended": bool(rec.get("recommended") and rec["recommended"]["topic_id"] == topic_id),
        "prerequisite_warning": warning,
        "href": "/learning-sessions",
        "note": "The AI Lecturer will use the selected topic. SYS will not silently redirect you to another subject or topic.",
    }


def evaluate_course_balance(
    db: Session,
    *,
    student_id: int,
    course_id: int,
) -> Dict[str, Any]:
    subjects = _course_subjects(db, course_id)
    weights = {
        w.subject_id: float(w.weight_percent)
        for w in db.query(models.SubjectWeightage).filter(models.SubjectWeightage.course_id == course_id).all()
    }
    now = _utcnow()
    recent_cut = now - timedelta(days=14)
    rows = []
    for sub in subjects:
        topics = _subject_topics(db, sub.id)
        tids = [t.id for t in topics]
        states = (
            db.query(models.TopicMasteryState)
            .filter(
                models.TopicMasteryState.student_id == student_id,
                models.TopicMasteryState.course_id == course_id,
                models.TopicMasteryState.topic_id.in_(tids or [-1]),
            )
            .all()
        )
        mastered = sum(1 for s in states if s.status == "MASTERED")
        support = sum(1 for s in states if s.status in SUPPORT_STATUSES)
        total = len(topics)
        coverage = round(100.0 * mastered / total, 1) if total else 0.0
        gaps = (
            db.query(models.LearningGap)
            .filter(
                models.LearningGap.student_id == student_id,
                models.LearningGap.course_id == course_id,
                models.LearningGap.scope_type == "TOPIC",
                models.LearningGap.scope_id.in_(tids or [-1]),
            )
            .all()
        )
        active_gaps = [g for g in gaps if not _gap_resolved(g) and g.classification in ACTIVE_GAP_CLASS]
        recent = (
            db.query(models.MasteryEvent)
            .filter(
                models.MasteryEvent.student_id == student_id,
                models.MasteryEvent.course_id == course_id,
                models.MasteryEvent.topic_id.in_(tids or [-1]),
                models.MasteryEvent.created_at >= recent_cut,
            )
            .count()
            if tids
            else 0
        )
        rows.append(
            {
                "subject_id": sub.id,
                "subject_name": sub.name,
                "total_topics": total,
                "mastered_topics": mastered,
                "needs_support": support,
                "coverage_percent": coverage,
                "active_gaps": len(active_gaps),
                "recent_mastery_events": recent,
                "weight_percent": weights.get(sub.id),
            }
        )

    comparable = [r for r in rows if r["total_topics"] > 0]
    status = "BALANCED"
    lagging = None
    leading = None
    delta = 0.0
    evidence: List[str] = []
    reason = "Not enough subject evidence to assess course balance."
    recommended_action = "Continue choosing subjects freely. SYS does not require a subject sequence."

    if len(comparable) < 2:
        reason = "Course balance is assessed across multiple subjects. A single-subject course is treated as balanced."
        status = "BALANCED"
    elif all(r["coverage_percent"] == 0 and r["mastered_topics"] == 0 for r in comparable):
        reason = "No subject has substantial progress yet, so differences are not treated as imbalance."
        status = "BALANCED"
    else:
        ranked = sorted(comparable, key=lambda r: (r["coverage_percent"], r["mastered_topics"]))
        lagging = ranked[0]
        others = ranked[1:]
        lead_cov = max(r["coverage_percent"] for r in others)
        lead_mastered = max(r["mastered_topics"] for r in others)
        leading = max(others, key=lambda r: (r["coverage_percent"], r["mastered_topics"]))
        delta = round(lead_cov - lagging["coverage_percent"], 1)
        substantial_lead = lead_cov >= DEFAULT_BALANCE_LEAD_COVERAGE or lead_mastered >= DEFAULT_BALANCE_LEAD_MASTERED
        extra = lagging["active_gaps"] > 0 or lagging["needs_support"] > 0 or lagging["recent_mastery_events"] < max(
            (r["recent_mastery_events"] for r in others), default=0
        )
        evidence = [
            f"{lagging['subject_name']} coverage={lagging['coverage_percent']}% ({lagging['mastered_topics']}/{lagging['total_topics']} mastered)",
            f"{leading['subject_name']} coverage={leading['coverage_percent']}% ({leading['mastered_topics']}/{leading['total_topics']} mastered)",
            f"Coverage gap={delta} points",
            f"Active P0-012 gaps in lagging subject={lagging['active_gaps']}",
            f"P0-015 needs-support topics={lagging['needs_support']}",
            f"Recent mastery events (14d) lagging={lagging['recent_mastery_events']} vs leading={leading['recent_mastery_events']}",
        ]
        if not substantial_lead or delta < DEFAULT_BALANCE_WATCH_POINTS:
            status = "BALANCED"
            reason = "Subject progress differences are within a normal range for autonomous study."
        else:
            if delta >= DEFAULT_BALANCE_URGENT_POINTS and extra:
                status = "URGENT_ATTENTION"
            elif delta >= DEFAULT_BALANCE_ATTENTION_POINTS:
                status = "ATTENTION_REQUIRED"
            else:
                status = "WATCH"
            reason = (
                f"You have made stronger progress in {leading['subject_name']}, but {lagging['subject_name']} "
                f"is significantly behind your other subjects in this course. If this imbalance continues, "
                f"it may affect overall examination preparation."
            )
            recommended_action = (
                f"Consider allocating additional study time to {lagging['subject_name']}. "
                "This is a recommendation — you may continue studying any subject."
            )

    signal = None
    if status in ("WATCH", "ATTENTION_REQUIRED", "URGENT_ATTENTION") and lagging:
        signal = {
            "code": "SUBJECT_PROGRESS_IMBALANCE",
            "severity": status,
            "student_id": student_id,
            "course_id": course_id,
            "topic_id": None,
            "topic_name": lagging["subject_name"],
            "title": f"Course balance: {lagging['subject_name']} is behind",
            "reason": reason,
            "evidence": evidence,
            "recommended_action": "ALLOCATE_TIME_TO_LAGGING_SUBJECT",
            "source_of_truth": [
                "P0-015_TopicMasteryState",
                "P0-012_LearningGap",
                "P0-015_MasteryEvent",
                "curriculum_Subject_Topic",
            ],
            "does_not_force_subject_switch": True,
        }

    return {
        "student_id": student_id,
        "course_id": course_id,
        "balance_status": status,
        "reason": reason,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "lagging_subject": lagging,
        "leading_subject": leading,
        "coverage_gap_points": delta,
        "subjects": rows,
        "signal": signal,
        "subject_order_imposed": False,
        "note": "Imbalance warnings never prevent you from choosing another subject.",
    }


def maybe_notify_imbalance(db: Session, *, student_id: int, course_id: int, balance: Dict[str, Any]) -> bool:
    sig = balance.get("signal")
    if not sig or sig.get("severity") not in ("ATTENTION_REQUIRED", "URGENT_ATTENTION"):
        return False
    cutoff = _utcnow() - timedelta(days=7)
    last = (
        db.query(models.Notification)
        .filter(
            models.Notification.student_id == student_id,
            models.Notification.course_id == course_id,
            models.Notification.event == "SUBJECT_PROGRESS_IMBALANCE",
            models.Notification.created_at >= cutoff,
        )
        .order_by(models.Notification.id.desc())
        .first()
    )
    last_sev = (last.payload or {}).get("severity") if last and last.payload else None
    rank = {"WATCH": 1, "ATTENTION_REQUIRED": 2, "URGENT_ATTENTION": 3}
    if last and rank.get(sig["severity"], 0) <= rank.get(last_sev or "", 0):
        return False
    notif_svc.emit_event(
        db,
        event="SUBJECT_PROGRESS_IMBALANCE",
        title=sig["title"],
        message=sig["reason"],
        student_id=student_id,
        course_id=course_id,
        severity="CRITICAL" if sig["severity"] == "URGENT_ATTENTION" else "WARNING",
        source_module="SUBJECT_PROGRESSION",
        link_path="/learning-journey/me",
        payload=sig,
        channels=["IN_APP"],
        dispatch=True,
    )
    return True


def subject_view(
    db: Session,
    actor: models.User,
    *,
    student_id: int,
    course_id: int,
    subject_id: int,
    notify: bool = False,
) -> Dict[str, Any]:
    _authorize_student_view(db, actor, student_id, course_id)
    if (actor.role or "").lower() == "student":
        _require_enrollment(db, student_id, course_id)
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject or subject.course_id != course_id:
        raise _http(404, "Subject is not part of this course")
    focus_subject(db, actor, student_id=student_id, course_id=course_id, subject_id=subject_id)
    rec = recommend_topic_in_subject(db, student_id=student_id, course_id=course_id, subject_id=subject_id)
    focus = (
        db.query(models.StudentSubjectFocus)
        .filter(
            models.StudentSubjectFocus.student_id == student_id,
            models.StudentSubjectFocus.course_id == course_id,
            models.StudentSubjectFocus.subject_id == subject_id,
        )
        .first()
    )
    balance = evaluate_course_balance(db, student_id=student_id, course_id=course_id)
    if notify:
        maybe_notify_imbalance(db, student_id=student_id, course_id=course_id, balance=balance)
    override_topic = None
    if focus and focus.selected_topic_id:
        t = db.query(models.Topic).filter(models.Topic.id == focus.selected_topic_id).first()
        if t and t.subject_id == subject_id:
            override_topic = {"topic_id": t.id, "topic_name": t.name}
    return {
        "course_id": course_id,
        "student_id": student_id,
        "subject": {"id": subject.id, "name": subject.name},
        "selected_subject": {"id": subject.id, "name": subject.name},
        "recommended_topic": rec.get("recommended"),
        "reason": rec.get("reason"),
        "prerequisite_warning": rec.get("prerequisite_warning"),
        "alternatives": rec.get("alternatives"),
        "topics": rec.get("topics"),
        "override_topic": override_topic,
        "course_balance": {
            "status": balance["balance_status"],
            "reason": balance["reason"],
            "lagging_subject": balance.get("lagging_subject"),
            "recommended_action": balance["recommended_action"],
            "subjects": balance["subjects"],
            "does_not_force_subject_switch": True,
        },
        "href_start_learning": "/learning-sessions",
        "subject_order_imposed": False,
        "authority_note": rec.get("authority_note"),
    }


def add_prerequisite(
    db: Session,
    actor: models.User,
    *,
    topic_id: int,
    prerequisite_topic_id: int,
) -> Dict[str, Any]:
    from app.academic_auth import require_assessment_designer

    if topic_id == prerequisite_topic_id:
        raise _http(422, "A topic cannot be a prerequisite of itself")
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    prereq = db.query(models.Topic).filter(models.Topic.id == prerequisite_topic_id).first()
    if not topic or not prereq:
        raise _http(404, "Topic not found")
    if topic.subject_id != prereq.subject_id:
        raise _http(422, "Prerequisites must be in the same subject")
    subject = db.query(models.Subject).filter(models.Subject.id == topic.subject_id).first()
    if subject and subject.course_id:
        require_assessment_designer(db, actor, subject.course_id)
    elif not is_admin(actor):
        raise _http(403, "Insufficient permissions")
    existing = (
        db.query(models.TopicPrerequisite)
        .filter(
            models.TopicPrerequisite.topic_id == topic_id,
            models.TopicPrerequisite.prerequisite_topic_id == prerequisite_topic_id,
        )
        .first()
    )
    if existing:
        return {"id": existing.id, "topic_id": topic_id, "prerequisite_topic_id": prerequisite_topic_id}
    row = models.TopicPrerequisite(
        topic_id=topic_id,
        prerequisite_topic_id=prerequisite_topic_id,
        created_by=actor.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "topic_id": topic_id, "prerequisite_topic_id": prerequisite_topic_id}


def list_prerequisites(db: Session, topic_id: int) -> List[Dict[str, Any]]:
    rows = db.query(models.TopicPrerequisite).filter(models.TopicPrerequisite.topic_id == topic_id).all()
    out = []
    for r in rows:
        t = db.query(models.Topic).filter(models.Topic.id == r.prerequisite_topic_id).first()
        out.append(
            {
                "id": r.id,
                "topic_id": r.topic_id,
                "prerequisite_topic_id": r.prerequisite_topic_id,
                "prerequisite_name": t.name if t else None,
            }
        )
    return out


def faculty_course_balance(db: Session, actor: models.User, *, course_id: int) -> Dict[str, Any]:
    _authorize_faculty_course(db, actor, course_id)
    enrollments = (
        db.query(models.StudentCourseEnrollment)
        .filter(models.StudentCourseEnrollment.course_id == course_id)
        .all()
    )
    students = []
    counts = {"BALANCED": 0, "WATCH": 0, "ATTENTION_REQUIRED": 0, "URGENT_ATTENTION": 0}
    for enr in enrollments:
        bal = evaluate_course_balance(db, student_id=enr.student_id, course_id=course_id)
        counts[bal["balance_status"]] = counts.get(bal["balance_status"], 0) + 1
        if bal["balance_status"] == "BALANCED":
            continue
        user = db.query(models.User).filter(models.User.id == enr.student_id).first()
        students.append(
            {
                "student_id": enr.student_id,
                "student_name": user.name if user else None,
                "balance_status": bal["balance_status"],
                "reason": bal["reason"],
                "lagging_subject": bal.get("lagging_subject"),
                "evidence": bal.get("evidence"),
            }
        )
    return {
        "course_id": course_id,
        "status_counts": counts,
        "students_needing_attention": students,
        "note": "Advisory only. Faculty cannot edit mastery from this view.",
    }


def admin_balance_overview(db: Session, actor: models.User, *, course_id: Optional[int] = None) -> Dict[str, Any]:
    if not is_admin(actor):
        raise _http(403, "Admin access required")
    q = db.query(models.Course)
    if course_id is not None:
        q = q.filter(models.Course.id == course_id)
    courses = q.all()
    out = []
    for c in courses:
        data = faculty_course_balance(db, actor, course_id=c.id)
        out.append(
            {
                "course_id": c.id,
                "course_title": c.title,
                "status_counts": data["status_counts"],
                "attention_count": len(data["students_needing_attention"]),
            }
        )
    return {"courses": out, "note": "Aggregates only unless a course filter is supplied with faculty student rows."}
