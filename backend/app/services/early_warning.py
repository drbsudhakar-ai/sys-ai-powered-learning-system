"""P0-016 Early-Warning Analytics — deterministic, evidence-backed signals only.

Does not calculate mastery or invent gaps. Consumes P0-012 gaps and P0-015 mastery.
No opaque AI risk scores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.constants import (
    DEFAULT_GAP_PERSISTENCE_DAYS,
    DEFAULT_LIMITED_IMPROVEMENT_POINTS,
    DEFAULT_MIN_BELOW_THRESHOLD_ATTEMPTS,
    DEFAULT_MIN_EVIDENCE_COUNT,
    DEFAULT_MIN_REASSESSMENT_FAILURES,
)
from app.services import mastery_engine as mastery


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_warning_policy(db: Session, course_id: Optional[int] = None) -> Dict[str, Any]:
    """Central early-warning thresholds (defaults + mastery policy linkage)."""
    mp = mastery.get_policy(db, course_id)
    return {
        "course_id": course_id,
        "mastery_threshold": mp["mastery_threshold"],
        "practice_threshold": mp["practice_threshold"],
        "reassessment_threshold": mp["reassessment_threshold"],
        "gap_persistence_days": DEFAULT_GAP_PERSISTENCE_DAYS,
        "min_below_threshold_attempts": DEFAULT_MIN_BELOW_THRESHOLD_ATTEMPTS,
        "min_reassessment_failures": DEFAULT_MIN_REASSESSMENT_FAILURES,
        "min_evidence_count": DEFAULT_MIN_EVIDENCE_COUNT,
        "limited_improvement_points": DEFAULT_LIMITED_IMPROVEMENT_POINTS,
        "regression_drop_points": mp["regression_drop_points"],
        "source": "constants+mastery_policy",
    }


def _gap_resolved(gap: models.LearningGap) -> bool:
    inf = gap.inference or {}
    return str(inf.get("mastery_status") or "").upper() == "RESOLVED"


def _topic_name(db: Session, topic_id: Optional[int], fallback: str = "") -> str:
    if not topic_id:
        return fallback or "Topic"
    t = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    return t.name if t else (fallback or f"Topic {topic_id}")


def evaluate_student_warnings(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    policy: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return explainable early-warning / progress signals for one student+course."""
    policy = policy or get_warning_policy(db, course_id)
    thr = float(policy["mastery_threshold"])
    persist_days = int(policy["gap_persistence_days"])
    min_below = int(policy["min_below_threshold_attempts"])
    min_fail = int(policy["min_reassessment_failures"])
    min_ev = int(policy["min_evidence_count"])
    lim_pts = float(policy["limited_improvement_points"])
    now = _utcnow()
    signals: List[Dict[str, Any]] = []

    states = (
        db.query(models.TopicMasteryState)
        .filter(
            models.TopicMasteryState.student_id == student_id,
            models.TopicMasteryState.course_id == course_id,
        )
        .all()
    )
    state_by_topic = {s.topic_id: s for s in states}

    gaps = (
        db.query(models.LearningGap)
        .filter(
            models.LearningGap.student_id == student_id,
            models.LearningGap.course_id == course_id,
            models.LearningGap.scope_type == "TOPIC",
        )
        .all()
    )

    # --- Persistent learning gap ---
    for g in gaps:
        if _gap_resolved(g):
            continue
        if g.classification not in ("WEAK", "CRITICAL_GAP", "DEVELOPING"):
            continue
        created = g.created_at or now
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (now - created).days
        topic_id = g.scope_id
        state = state_by_topic.get(topic_id) if topic_id else None
        if age_days < persist_days and not (state and state.status in ("NEEDS_REMEDIATION", "MASTERY_REGRESSED")):
            continue
        if age_days < persist_days and state and state.status == "MASTERED":
            continue
        evidence = [
            f"Active topic gap classification={g.classification}",
            f"Gap age ≈ {age_days} days (persistence threshold={persist_days})",
        ]
        if state:
            evidence.append(f"Current mastery status={state.status} (from P0-015)")
        severity = "URGENT_ATTENTION" if g.classification == "CRITICAL_GAP" or age_days >= persist_days * 2 else "ATTENTION_REQUIRED"
        signals.append(
            {
                "code": "PERSISTENT_LEARNING_GAP",
                "severity": severity,
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id, g.scope_name or ""),
                "title": "Needs additional support — persistent learning gap",
                "reason": (
                    f"Unresolved topic gap has persisted across the configured period "
                    f"({persist_days} days) and mastery criteria have not been met."
                ),
                "evidence": evidence,
                "recommended_action": "FURTHER_SUPPORT_RECOMMENDED",
                "source_of_truth": ["P0-012_LearningGap", "P0-015_TopicMasteryState"],
            }
        )

    # --- Repeated assessment difficulty (same topic) ---
    for topic_id, state in state_by_topic.items():
        fails = (
            db.query(models.MasteryEvent)
            .filter(
                models.MasteryEvent.student_id == student_id,
                models.MasteryEvent.course_id == course_id,
                models.MasteryEvent.topic_id == topic_id,
                models.MasteryEvent.event_type.in_(("REASSESSMENT_FAILED", "PRACTICE_EVALUATED")),
            )
            .order_by(models.MasteryEvent.created_at.desc())
            .limit(20)
            .all()
        )
        below = 0
        for ev in fails:
            evid = ev.evidence or {}
            pct = evid.get("percentage")
            if pct is None:
                continue
            if float(pct) < thr:
                below += 1
        if below < min_below:
            continue
        if state.status == "MASTERED":
            continue
        signals.append(
            {
                "code": "REPEATED_ASSESSMENT_DIFFICULTY",
                "severity": "ATTENTION_REQUIRED",
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id),
                "title": "Repeated below-threshold performance on this topic",
                "reason": (
                    f"At least {below} recent topic attempts scored below the mastery "
                    f"threshold ({thr}%)."
                ),
                "evidence": [
                    f"Below-threshold attempts counted={below} (min={min_below})",
                    f"Current status={state.status}",
                    f"Mastery threshold={thr}%",
                ],
                "recommended_action": "ATTENTION_REQUIRED",
                "source_of_truth": ["P0-015_MasteryEvent", "P0-015_TopicMasteryState"],
            }
        )

    # --- Reassessment failure ---
    for topic_id, state in state_by_topic.items():
        fail_events = (
            db.query(models.MasteryEvent)
            .filter(
                models.MasteryEvent.student_id == student_id,
                models.MasteryEvent.course_id == course_id,
                models.MasteryEvent.topic_id == topic_id,
                models.MasteryEvent.event_type == "REASSESSMENT_FAILED",
            )
            .count()
        )
        if fail_events < min_fail:
            continue
        signals.append(
            {
                "code": "REASSESSMENT_FAILURE",
                "severity": "ATTENTION_REQUIRED",
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id),
                "title": "Reassessment did not meet mastery criteria",
                "reason": "Reassessment was attempted and mastery criteria were not met.",
                "evidence": [
                    f"Reassessment failure events={fail_events}",
                    f"Current status={state.status}",
                    f"Mastery percent={state.mastery_percent}",
                ],
                "recommended_action": "FURTHER_PRACTICE_OR_REMEDIATION",
                "source_of_truth": ["P0-015_MasteryEvent"],
            }
        )

    # --- Limited improvement after remediation + practice ---
    interventions = (
        db.query(models.RemedialIntervention)
        .filter(
            models.RemedialIntervention.course_id == course_id,
            models.RemedialIntervention.status == "COMPLETED",
        )
        .all()
    )
    member_group_ids = {
        r[0]
        for r in db.query(models.RemedialGroupMember.group_id)
        .filter(models.RemedialGroupMember.student_id == student_id)
        .all()
    }
    for iv in interventions:
        student_match = iv.student_id == student_id
        group_match = iv.group_id and iv.group_id in member_group_ids
        if not (student_match or group_match):
            continue
        snap = iv.gap_snapshot or {}
        topic_id = snap.get("scope_id") if snap.get("scope_type") == "TOPIC" else None
        if not topic_id and iv.learning_gap_id:
            lg = db.query(models.LearningGap).filter(models.LearningGap.id == iv.learning_gap_id).first()
            if lg and lg.scope_type == "TOPIC":
                topic_id = lg.scope_id
        if not topic_id:
            continue
        state = state_by_topic.get(topic_id)
        if not state or state.practice_accuracy is None:
            continue
        if state.status in ("MASTERED", "READY_FOR_REASSESSMENT"):
            continue
        if float(state.practice_accuracy) >= float(policy["reassessment_threshold"]):
            continue
        signals.append(
            {
                "code": "LIMITED_IMPROVEMENT",
                "severity": "WATCH",
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id),
                "title": "Limited improvement after remediation and practice",
                "reason": (
                    "Remediation and practice evidence exist, but performance has not yet "
                    "reached the configured reassessment readiness threshold."
                ),
                "evidence": [
                    f"Intervention id={iv.id} status={iv.status}",
                    f"Practice accuracy={state.practice_accuracy}%",
                    f"Reassessment threshold={policy['reassessment_threshold']}%",
                    f"Current status={state.status}",
                ],
                "recommended_action": "FURTHER_SUPPORT_RECOMMENDED",
                "source_of_truth": ["P0-014_RemedialIntervention", "P0-015_TopicMasteryState"],
                "association_note": "Observational association — not a causal claim",
            }
        )

    # --- Mastery regression ---
    for topic_id, state in state_by_topic.items():
        if state.status != "MASTERY_REGRESSED":
            reg_ev = (
                db.query(models.MasteryEvent)
                .filter(
                    models.MasteryEvent.student_id == student_id,
                    models.MasteryEvent.course_id == course_id,
                    models.MasteryEvent.topic_id == topic_id,
                    models.MasteryEvent.event_type == "MASTERY_REGRESSED",
                )
                .first()
            )
            if not reg_ev:
                continue
        signals.append(
            {
                "code": "MASTERY_REGRESSION",
                "severity": "ATTENTION_REQUIRED",
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id),
                "title": "Previously mastered topic shows meaningful decline",
                "reason": "Authoritative mastery state indicates regression after prior mastery.",
                "evidence": [
                    f"Current status={state.status}",
                    f"Mastery percent={state.mastery_percent}",
                    "Regression rule is conservative (P0-015); single minor mistakes do not trigger this.",
                ],
                "recommended_action": "REVIEW_RECOMMENDED",
                "source_of_truth": ["P0-015_TopicMasteryState", "P0-015_MasteryEvent"],
            }
        )

    # --- Positive progress (needs multiple evidence points) ---
    for topic_id, state in state_by_topic.items():
        events = (
            db.query(models.MasteryEvent)
            .filter(
                models.MasteryEvent.student_id == student_id,
                models.MasteryEvent.course_id == course_id,
                models.MasteryEvent.topic_id == topic_id,
            )
            .order_by(models.MasteryEvent.created_at.asc())
            .all()
        )
        if len(events) < min_ev:
            continue
        improved = False
        if state.status == "MASTERED":
            prior_weak = any(
                e.from_status in ("NEEDS_REMEDIATION", "NEEDS_PRACTICE", "MASTERY_REGRESSED", "LEARNING")
                for e in events
                if e.to_status == "MASTERED"
            )
            improved = prior_weak
        elif state.status in ("READY_FOR_REASSESSMENT", "LEARNING") and state.practice_accuracy:
            # practice trend from events
            practice_pcts = []
            for e in events:
                if e.event_type == "PRACTICE_EVALUATED" and (e.evidence or {}).get("percentage") is not None:
                    practice_pcts.append(float(e.evidence["percentage"]))
            if len(practice_pcts) >= 2 and practice_pcts[-1] > practice_pcts[0] + lim_pts:
                improved = True
        if not improved:
            continue
        signals.append(
            {
                "code": "POSITIVE_PROGRESS",
                "severity": "INFO",
                "student_id": student_id,
                "course_id": course_id,
                "topic_id": topic_id,
                "topic_name": _topic_name(db, topic_id),
                "title": "Positive learning progress",
                "reason": "Prior weakness followed by repeated improvement and/or mastery progression.",
                "evidence": [
                    f"Current status={state.status}",
                    f"Mastery percent={state.mastery_percent}",
                    f"Practice accuracy={state.practice_accuracy}",
                    f"Supporting mastery events={len(events)}",
                ],
                "recommended_action": "POSITIVE_PROGRESS",
                "source_of_truth": ["P0-015_MasteryEvent", "P0-015_TopicMasteryState"],
            }
        )

    # Deduplicate by (code, topic_id)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for s in signals:
        key = (s["code"], s.get("topic_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    severity_rank = {"URGENT_ATTENTION": 0, "ATTENTION_REQUIRED": 1, "WATCH": 2, "INFO": 3}
    unique.sort(key=lambda x: (severity_rank.get(x["severity"], 9), x.get("topic_name") or ""))

    # P0-019 course-level subject imbalance (derived from P0-015/P0-012; not a new risk score)
    from app.services import subject_progression as sp

    balance = sp.evaluate_course_balance(db, student_id=student_id, course_id=course_id)
    if balance.get("signal"):
        unique.append(balance["signal"])
        unique.sort(key=lambda x: (severity_rank.get(x["severity"], 9), x.get("topic_name") or ""))
    return unique


def recommend_for_status(status: str, *, has_persistent_gap: bool = False) -> Dict[str, str]:
    """Student-facing advisory recommendation from authoritative status."""
    s = (status or "").upper()
    if s == "MASTERED":
        return {"action": "CONTINUE", "message": "Continue to the next topic."}
    if s == "READY_FOR_REASSESSMENT":
        return {"action": "TAKE_REASSESSMENT", "message": "Take the reassessment when ready."}
    if s == "NEEDS_PRACTICE":
        return {"action": "START_PRACTICE", "message": "Start adaptive practice for this topic."}
    if s in ("NEEDS_REMEDIATION", "REMEDIATION_IN_PROGRESS", "MASTERY_REGRESSED"):
        if has_persistent_gap:
            return {
                "action": "CONSIDER_REMEDIAL",
                "message": "Consider remedial learning or additional subject-expert support.",
            }
        return {
            "action": "PRACTICE_OR_REMEDIATE",
            "message": "Continue targeted practice; consider remedial support if needed.",
        }
    if s == "LEARNING":
        return {"action": "CONTINUE_PATH", "message": "Continue the current learning path — you are improving."}
    if s == "REASSESSMENT_PENDING":
        return {"action": "COMPLETE_REASSESSMENT", "message": "Complete the pending reassessment."}
    return {"action": "REVIEW", "message": "Review this topic when you are ready."}


def faculty_recommendation(
    *,
    code: str,
    status: str,
    same_gap_student_count: int = 1,
) -> Dict[str, str]:
    """Advisory faculty recommendation (does not automate interventions)."""
    if code == "POSITIVE_PROGRESS" or status == "MASTERED":
        return {
            "action": "NO_FURTHER_REMEDIATION",
            "message": "Mastered or improving — no further remediation required for this topic.",
        }
    if code == "PERSISTENT_LEARNING_GAP" and same_gap_student_count >= 3:
        return {
            "action": "CONSIDER_COMMON_SESSION",
            "message": "Multiple students share this gap — consider a COMMON remedial session.",
        }
    if code == "PERSISTENT_LEARNING_GAP":
        return {
            "action": "CONSIDER_INDIVIDUAL_OR_EXPERT",
            "message": "Consider INDIVIDUAL intervention or additional subject-expert teaching.",
        }
    if code == "REASSESSMENT_FAILURE":
        return {
            "action": "ENCOURAGE_PRACTICE",
            "message": "Practice may improve but reassessment failed — encourage additional targeted practice.",
        }
    if code == "LIMITED_IMPROVEMENT":
        return {
            "action": "FURTHER_SUPPORT",
            "message": "Further support recommended after remediation and practice.",
        }
    if code == "MASTERY_REGRESSION":
        return {
            "action": "REVIEW",
            "message": "Review recommended — mastery regression detected from later evidence.",
        }
    if code == "SUBJECT_PROGRESS_IMBALANCE":
        return {
            "action": "ENCOURAGE_LAGGING_SUBJECT_TIME",
            "message": "Advise additional study time for the lagging subject without forcing a subject switch.",
        }
    return {"action": "MONITOR", "message": "Monitor progress and offer support as needed."}
