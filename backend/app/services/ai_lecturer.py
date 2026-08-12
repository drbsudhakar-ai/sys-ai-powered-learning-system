"""AI Lecturer orchestrator — digital classroom teaching layer (P0-013.4).

Consumes P0-013.3 Learning Session infrastructure. Does not create a parallel
session model. Teaching plans live on LECTURE activity.payload; per-participant
progress is recorded as LearningEvidence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.constants import (
    TEACHING_INTERACTION_INTENTS,
    TEACHING_LECTURE_STATUSES,
    TEACHING_PLAYBACK_ACTIONS,
    TEACHING_STEP_CONTROL_ACTIONS,
)
from app.services import learning_sessions as ls
from app.services.ai_provider import get_ai_provider
from app.services.narration import get_narration_provider
from app.services.teaching_plans import (
    build_remediation_steps,
    build_teaching_plan,
    enrich_step_narration,
    validate_teaching_plan,
)


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _topic_title(db: Session, session: models.LearningSession) -> str:
    if session.topic_id:
        t = db.query(models.Topic).filter(models.Topic.id == session.topic_id).first()
        if t:
            return t.name
    return session.title or ""


def _subject_name(db: Session, session: models.LearningSession) -> str:
    if session.subject_id:
        s = db.query(models.Subject).filter(models.Subject.id == session.subject_id).first()
        if s:
            return s.name
    return ""


def _find_lecture_activity(
    session: models.LearningSession,
    actor: models.User,
    db: Session,
) -> Optional[models.LearningSessionActivity]:
    activities = ls.list_activities_for_user(db, actor, session.id)
    lecture_acts = [a for a in activities if (a.activity_type or "").upper() == "LECTURE"]
    if not lecture_acts:
        # Managers may see all; students might only see common lecture
        all_acts = sorted(session.activities or [], key=lambda a: (a.sequence, a.id))
        lecture_acts = [a for a in all_acts if (a.activity_type or "").upper() == "LECTURE"]
        lecture_acts = [a for a in lecture_acts if ls.activity_visible_to_user(db, actor, session, a)]
    return lecture_acts[0] if lecture_acts else None


def _ensure_lecture_activity(
    db: Session,
    actor: models.User,
    session: models.LearningSession,
) -> models.LearningSessionActivity:
    existing = _find_lecture_activity(session, actor, db)
    if existing:
        return existing
    # Only managers create the shared lecture activity
    if not ls._can_manage(db, actor, session):
        # Student opening: allow if manager already created, else create via system path
        # Re-check without visibility for managers creating on first student open —
        # facilitators should open first; for INDIVIDUAL student can trigger generation
        # if they can view and no lecture exists yet: require manage OR individual primary student
        students = [
            p
            for p in (session.participants or [])
            if p.role == "STUDENT" and p.status != "REMOVED"
        ]
        is_primary = any(p.user_id == actor.id for p in students) and (
            session.mode == "INDIVIDUAL" or len(students) >= 1
        )
        if not is_primary:
            raise _http(403, "Lecture activity not available; facilitator must prepare the lecture")
    plan = _generate_plan(db, session)
    # Persist via add_activity when actor can manage; otherwise insert under facilitator
    manager = actor
    if not ls._can_manage(db, actor, session):
        fac = (
            db.query(models.User).filter(models.User.id == session.facilitator_id).first()
            if session.facilitator_id
            else None
        )
        creator = (
            db.query(models.User).filter(models.User.id == session.created_by).first()
            if session.created_by
            else None
        )
        manager = fac or creator or actor
    row = ls.add_activity(
        db,
        manager,
        session.id,
        activity_type="LECTURE",
        title=f"AI Lecture — {session.title}",
        description="Digital classroom teaching sequence",
        sequence=1,
        scope="COMMON",
        payload={
            "teaching_plan": plan,
            "lecture_meta": {"provider": "ai_lecturer", "version": 1},
        },
    )
    return row


def _generate_plan(db: Session, session: models.LearningSession) -> Dict[str, Any]:
    topic = _topic_title(db, session)
    subject = _subject_name(db, session)
    objectives = [o.statement for o in sorted(session.objectives or [], key=lambda x: x.sequence)]
    provider = get_ai_provider()
    # Provider returns structured signal; lecturer assembles validated plan (no raw UI code)
    provider.complete_json(
        system="You are the SYS AI Lecturer planner. Propose teaching structure only.",
        user=f"Create a step-by-step teaching plan for: {session.title}. Topic: {topic}.",
        context={
            "intent": "TEACHING_PLAN",
            "session_id": session.id,
            "session_title": session.title,
            "topic_title": topic,
            "subject_name": subject,
            "mode": session.mode,
            "objectives": objectives,
        },
    )
    return build_teaching_plan(
        title=session.title,
        topic_title=topic,
        subject_name=subject,
        objectives=objectives,
    )


def _latest_progress(
    db: Session,
    session_id: int,
    user_id: int,
    activity_id: int,
) -> Dict[str, Any]:
    rows = (
        db.query(models.LearningEvidence)
        .filter(
            models.LearningEvidence.session_id == session_id,
            models.LearningEvidence.user_id == user_id,
            models.LearningEvidence.activity_id == activity_id,
            models.LearningEvidence.event_type.in_(
                (
                    "TEACHING_OPENED",
                    "TEACHING_STEP_REACHED",
                    "TEACHING_PAUSED",
                    "TEACHING_RESUMED",
                    "TEACHING_COMPLETED",
                )
            ),
        )
        .order_by(models.LearningEvidence.id.desc())
        .limit(20)
        .all()
    )
    state = {
        "current_step_index": 0,
        "status": "READY",
        "playback_rate": 1.0,
    }
    for row in rows:
        payload = row.payload or {}
        if "current_step_index" in payload:
            state["current_step_index"] = int(payload["current_step_index"])
        if "status" in payload and payload["status"] in TEACHING_LECTURE_STATUSES:
            state["status"] = payload["status"]
        if "playback_rate" in payload:
            state["playback_rate"] = float(payload["playback_rate"])
        break
    return state


def _record_progress(
    db: Session,
    actor: models.User,
    session: models.LearningSession,
    activity: models.LearningSessionActivity,
    *,
    event_type: str,
    state: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    part = ls.get_participant_row(db, session.id, user_id=actor.id)
    payload = {
        "current_step_index": state.get("current_step_index", 0),
        "status": state.get("status", "READY"),
        "playback_rate": state.get("playback_rate", 1.0),
        **(extra or {}),
    }
    ls.record_evidence(
        db,
        actor,
        session_id=session.id,
        event_type=event_type,
        user_id=actor.id,
        participant_id=part.id if part else None,
        activity_id=activity.id,
        payload=payload,
        commit=True,
    )


def _decorate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    narration = get_narration_provider()
    steps = []
    for step in plan.get("steps") or []:
        n = step.get("narration") or {}
        payload = narration.synthesize_step(
            text=n.get("text") or "",
            step_id=step.get("id") or "",
            duration_ms=int(n.get("duration_ms") or step.get("duration_ms") or 4000),
        )
        steps.append(enrich_step_narration(step, payload))
    out = dict(plan)
    out["steps"] = steps
    return out


def _lecture_response(
    db: Session,
    actor: models.User,
    session: models.LearningSession,
    activity: models.LearningSessionActivity,
    *,
    overlay_steps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload = activity.payload or {}
    plan = payload.get("teaching_plan")
    if not plan:
        plan = _generate_plan(db, session)
        merged = dict(payload)
        merged["teaching_plan"] = plan
        activity.payload = merged
        db.commit()
        db.refresh(activity)
    plan = validate_teaching_plan(plan)
    plan = _decorate_plan(plan)
    state = _latest_progress(db, session.id, actor.id, activity.id)
    steps = list(plan["steps"])
    if overlay_steps:
        # Insert remediation after current index for this response only (also persist appended?)
        # Persist into plan so replay works: append unique remediation steps
        existing_ids = {s["id"] for s in steps}
        for s in overlay_steps:
            if s["id"] not in existing_ids:
                steps.append(s)
                existing_ids.add(s["id"])
        plan["steps"] = steps
        merged = dict(activity.payload or {})
        merged["teaching_plan"] = {**plan, "steps": [dict(s) for s in steps]}
        # strip narration provider fields for storage compactness
        for st in merged["teaching_plan"]["steps"]:
            n = st.get("narration") or {}
            st["narration"] = {
                "text": n.get("text"),
                "duration_ms": n.get("duration_ms"),
            }
        validate_teaching_plan(merged["teaching_plan"])
        activity.payload = merged
        db.commit()
        db.refresh(activity)
        plan = _decorate_plan(validate_teaching_plan(merged["teaching_plan"]))
        steps = plan["steps"]

    idx = max(0, min(int(state["current_step_index"]), max(len(steps) - 1, 0)))
    current = steps[idx] if steps else None
    progress = ls.list_session_progress(db, actor, session.id)
    return {
        "session_id": session.id,
        "activity_id": activity.id,
        "title": session.title,
        "mode": session.mode,
        "session_status": session.status,
        "course_id": session.course_id,
        "subject_id": session.subject_id,
        "topic_id": session.topic_id,
        "subtopic_id": session.subtopic_id,
        "objectives": [
            {"id": o.id, "statement": o.statement, "sequence": o.sequence, "status": o.status}
            for o in sorted(session.objectives or [], key=lambda x: x.sequence)
        ],
        "teaching_plan": plan,
        "current_step_index": idx,
        "current_step": current,
        "lecture_status": state["status"],
        "playback_rate": state["playback_rate"],
        "step_count": len(steps),
        "interactions_available": list(TEACHING_INTERACTION_INTENTS),
        "controls": {
            "step": list(TEACHING_STEP_CONTROL_ACTIONS),
            "playback": list(TEACHING_PLAYBACK_ACTIONS),
        },
        "participant_progress": progress,
    }


def open_lecture(db: Session, actor: models.User, session_id: int) -> Dict[str, Any]:
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, actor, session)
    activity = _ensure_lecture_activity(db, actor, session)
    # Ensure plan present
    if not (activity.payload or {}).get("teaching_plan"):
        plan = _generate_plan(db, session)
        merged = dict(activity.payload or {})
        merged["teaching_plan"] = plan
        activity.payload = merged
        db.commit()
        db.refresh(activity)
    else:
        validate_teaching_plan((activity.payload or {})["teaching_plan"])

    state = _latest_progress(db, session.id, actor.id, activity.id)
    if state["status"] == "COMPLETED":
        # Re-open keeps completed unless they replay
        pass
    elif state["status"] == "READY":
        state = {**state, "status": "PLAYING"}
        _record_progress(
            db, actor, session, activity, event_type="TEACHING_OPENED", state=state
        )
    else:
        _record_progress(
            db, actor, session, activity, event_type="TEACHING_OPENED", state=state
        )

    # Move session into IN_PROGRESS if possible (non-fatal if already there)
    if session.status in ("DRAFT", "SCHEDULED", "READY") and ls._can_manage(db, actor, session):
        try:
            ls.start_session_flow(db, actor, session.id)
            session = ls.get_session(db, session_id)
        except HTTPException:
            pass
    elif session.status in ("DRAFT", "SCHEDULED", "READY"):
        # Student open: record activity started only
        pass

    part = ls.get_participant_row(db, session.id, user_id=actor.id)
    if part and part.status in ("INVITED", "JOINED"):
        try:
            ls.set_participant_status(db, actor, session.id, part.id, "ACTIVE")
        except HTTPException:
            pass

    activity = _find_lecture_activity(ls.get_session(db, session_id), actor, db) or activity
    return _lecture_response(db, actor, ls.get_session(db, session_id), activity)


def get_lecture(db: Session, actor: models.User, session_id: int) -> Dict[str, Any]:
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, actor, session)
    activity = _find_lecture_activity(session, actor, db)
    if not activity:
        raise _http(404, "Lecture not opened yet; call POST .../lecture/open")
    return _lecture_response(db, actor, session, activity)


def control_step(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    action: str,
    step_index: Optional[int] = None,
) -> Dict[str, Any]:
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, actor, session)
    activity = _find_lecture_activity(session, actor, db)
    if not activity:
        raise _http(404, "Lecture not opened yet")
    action = (action or "").upper()
    if action not in TEACHING_STEP_CONTROL_ACTIONS:
        raise _http(422, f"Invalid step action: {action}")
    plan = validate_teaching_plan((activity.payload or {}).get("teaching_plan") or {})
    n = len(plan["steps"])
    state = _latest_progress(db, session.id, actor.id, activity.id)
    idx = int(state["current_step_index"])
    if action == "NEXT":
        idx = min(idx + 1, n - 1)
    elif action == "PREV":
        idx = max(idx - 1, 0)
    elif action == "GOTO":
        if step_index is None:
            raise _http(422, "GOTO requires step_index")
        if step_index < 0 or step_index >= n:
            raise _http(422, "step_index out of range")
        idx = int(step_index)
    elif action == "REPLAY":
        # stay on current index; client re-animates
        pass
    state = {
        **state,
        "current_step_index": idx,
        "status": "PLAYING" if state["status"] != "COMPLETED" else state["status"],
    }
    _record_progress(
        db,
        actor,
        session,
        activity,
        event_type="TEACHING_STEP_REACHED",
        state=state,
        extra={"action": action},
    )
    return _lecture_response(db, actor, session, activity)


def control_playback(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    action: str,
) -> Dict[str, Any]:
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, actor, session)
    activity = _find_lecture_activity(session, actor, db)
    if not activity:
        raise _http(404, "Lecture not opened yet")
    action = (action or "").upper()
    if action not in TEACHING_PLAYBACK_ACTIONS:
        raise _http(422, f"Invalid playback action: {action}")
    state = _latest_progress(db, session.id, actor.id, activity.id)
    event = "TEACHING_STEP_REACHED"
    if action == "PAUSE":
        state["status"] = "PAUSED"
        event = "TEACHING_PAUSED"
    elif action == "RESUME":
        state["status"] = "PLAYING"
        event = "TEACHING_RESUMED"
    elif action == "SLOW_DOWN":
        state["playback_rate"] = max(0.5, float(state.get("playback_rate", 1.0)) - 0.25)
        state["status"] = "PLAYING"
    elif action == "SPEED_UP":
        state["playback_rate"] = min(2.0, float(state.get("playback_rate", 1.0)) + 0.25)
        state["status"] = "PLAYING"
    elif action == "COMPLETE":
        plan = validate_teaching_plan((activity.payload or {}).get("teaching_plan") or {})
        state["current_step_index"] = max(len(plan["steps"]) - 1, 0)
        state["status"] = "COMPLETED"
        event = "TEACHING_COMPLETED"
        # Mark activity completed for this participant via evidence (session status unchanged)
        ls.record_evidence(
            db,
            actor,
            session_id=session.id,
            event_type="ACTIVITY_COMPLETED",
            user_id=actor.id,
            activity_id=activity.id,
            payload={"source": "ai_lecturer"},
            commit=True,
        )
        part = ls.get_participant_row(db, session.id, user_id=actor.id)
        if part and part.role == "STUDENT":
            try:
                ls.set_participant_status(db, actor, session.id, part.id, "COMPLETED")
            except HTTPException:
                pass
    _record_progress(db, actor, session, activity, event_type=event, state=state, extra={"action": action})
    return _lecture_response(db, actor, session, activity)


def interact(
    db: Session,
    actor: models.User,
    session_id: int,
    *,
    intent: str,
    message: Optional[str] = None,
    answer: Optional[str] = None,
) -> Dict[str, Any]:
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, actor, session)
    activity = _find_lecture_activity(session, actor, db)
    if not activity:
        raise _http(404, "Lecture not opened yet")
    intent = (intent or "").upper()
    if intent not in TEACHING_INTERACTION_INTENTS:
        raise _http(422, f"Invalid interaction intent: {intent}")

    # Provider consulted for structured signal only
    get_ai_provider().complete_json(
        system="SYS AI Lecturer interaction. Respond via teaching steps, not chat walls.",
        user=message or intent,
        context={
            "intent": intent,
            "session_id": session.id,
            "answer": answer,
        },
    )

    state = _latest_progress(db, session.id, actor.id, activity.id)
    plan = validate_teaching_plan((activity.payload or {}).get("teaching_plan") or {})
    steps = plan["steps"]
    idx = int(state["current_step_index"])
    current = steps[idx] if steps else {}

    if intent == "GO_BACK":
        return control_step(db, actor, session_id, action="PREV")
    if intent == "CONTINUE":
        return control_step(db, actor, session_id, action="NEXT")
    if intent == "SLOW_DOWN":
        return control_playback(db, actor, session_id, action="SLOW_DOWN")

    overlay: List[Dict[str, Any]] = []
    if intent == "CHECK_UNDERSTANDING" and answer is not None:
        interaction = (current or {}).get("interaction") or {}
        correct = interaction.get("correct")
        ok = correct is None or str(answer).strip().lower() == str(correct).strip().lower()
        overlay = [
            {
                "id": f"chk-result-{idx}-{activity.id}",
                "kind": "EXPLANATION",
                "purpose": "check_result",
                "visual_type": "BOARD_MIXED",
                "board": {
                    "elements": [
                        {
                            "type": "heading",
                            "text": "Correct" if ok else "Let's review",
                            "id": "cr",
                        },
                        {
                            "type": "callout",
                            "text": (
                                "Well done — that matches the concept."
                                if ok
                                else "Not quite. Watch the board for a focused re-explanation."
                            ),
                            "id": "cm",
                        },
                    ],
                    "actions": ["reveal", "highlight"],
                },
                "visual": None,
                "narration": {
                    "text": (
                        "Correct. We can continue."
                        if ok
                        else "Let's revisit the key relationship on the board."
                    ),
                    "duration_ms": 4500,
                },
                "interaction": None,
                "duration_ms": 4500,
            }
        ]
        if not ok:
            overlay.extend(
                build_remediation_steps(
                    intent="EXPLAIN_AGAIN",
                    message=message or "",
                    current_step=current,
                    topic=_topic_title(db, session),
                )
            )
    else:
        overlay = build_remediation_steps(
            intent=intent,
            message=message or "",
            current_step=current,
            topic=_topic_title(db, session),
        )

    part = ls.get_participant_row(db, session.id, user_id=actor.id)
    ls.record_evidence(
        db,
        actor,
        session_id=session.id,
        event_type="TEACHING_INTERACTION",
        user_id=actor.id,
        participant_id=part.id if part else None,
        activity_id=activity.id,
        payload={"intent": intent, "message": message, "answer": answer},
        commit=True,
    )
    ls.record_evidence(
        db,
        actor,
        session_id=session.id,
        event_type="AI_INTERACTION",
        user_id=actor.id,
        participant_id=part.id if part else None,
        activity_id=activity.id,
        payload={"intent": intent},
        commit=True,
    )

    if overlay:
        # Move cursor to first new remediation step after persist
        before_count = len(steps)
        resp = _lecture_response(db, actor, session, activity, overlay_steps=overlay)
        new_idx = before_count  # first appended step
        if new_idx < resp["step_count"]:
            return control_step(db, actor, session_id, action="GOTO", step_index=new_idx)
        return resp
    return _lecture_response(db, actor, session, activity)
