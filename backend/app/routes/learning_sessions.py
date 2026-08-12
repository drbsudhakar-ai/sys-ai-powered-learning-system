"""P0-013.2 Learning Session Management APIs — thin HTTP over domain service."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.routes.auth import get_current_user
from app.services import learning_sessions as ls

router = APIRouter(prefix="/learning-sessions", tags=["Learning Sessions"])


def _out(session: models.LearningSession) -> schemas.LearningSessionOut:
    return schemas.LearningSessionOut.model_validate(ls.session_to_dict(session))


@router.post("", response_model=schemas.LearningSessionOut, status_code=status.HTTP_201_CREATED)
def create_learning_session(
    payload: schemas.LearningSessionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Creator is always the authenticated user; facilitator defaults to actor
    # (admins may optionally assign another facilitator).
    facilitator_id = None
    if (current_user.role or "").lower() == "admin" and payload.facilitator_id:
        facilitator_id = payload.facilitator_id
    session = ls.create_session(
        db,
        current_user,
        title=payload.title,
        description=payload.description,
        mode=payload.mode,
        course_id=payload.course_id,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        subtopic_id=payload.subtopic_id,
        facilitator_id=facilitator_id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        primary_student_id=payload.primary_student_id,
    )
    return _out(session)


@router.get("", response_model=List[schemas.LearningSessionOut])
def list_learning_sessions(
    course_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    topic_id: Optional[int] = Query(None),
    mode: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    sessions = ls.list_sessions_for_user(
        db,
        current_user,
        course_id=course_id,
        subject_id=subject_id,
        topic_id=topic_id,
        mode=mode,
        status_filter=status_filter,
    )
    return [_out(s) for s in sessions]


@router.get("/{session_id}", response_model=schemas.LearningSessionOut)
def get_learning_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, current_user, session)
    return _out(session)


@router.patch("/{session_id}", response_model=schemas.LearningSessionOut)
def update_learning_session(
    session_id: int,
    payload: schemas.LearningSessionUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    kwargs = {}
    for key in ("title", "description", "subject_id", "topic_id", "subtopic_id", "scheduled_start", "scheduled_end"):
        if key in data:
            kwargs[key] = data[key]
    session = ls.update_session(db, current_user, session_id, **kwargs)
    return _out(session)


@router.post("/{session_id}/transition", response_model=schemas.LearningSessionOut)
def transition_learning_session(
    session_id: int,
    payload: schemas.LearningSessionStatusChange,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = ls.transition_status(db, current_user, session_id, payload.status)
    return _out(session)


def _lifecycle(db, user, session_id: int, status_name: str):
    return _out(ls.transition_status(db, user, session_id, status_name))


@router.post("/{session_id}/start", response_model=schemas.LearningSessionOut)
def start_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _out(ls.start_session_flow(db, current_user, session_id))


@router.post("/{session_id}/pause", response_model=schemas.LearningSessionOut)
def pause_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _lifecycle(db, current_user, session_id, "PAUSED")


@router.post("/{session_id}/resume", response_model=schemas.LearningSessionOut)
def resume_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _lifecycle(db, current_user, session_id, "IN_PROGRESS")


@router.post("/{session_id}/complete", response_model=schemas.LearningSessionOut)
def complete_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _lifecycle(db, current_user, session_id, "COMPLETED")


@router.post("/{session_id}/cancel", response_model=schemas.LearningSessionOut)
def cancel_session(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _lifecycle(db, current_user, session_id, "CANCELLED")


# ---- Participants ----

@router.get("/{session_id}/participants", response_model=List[schemas.LearningParticipantOut])
def list_participants(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, current_user, session)
    return [p for p in session.participants if p.status != "REMOVED"]


@router.post(
    "/{session_id}/participants",
    response_model=schemas.LearningParticipantOut,
    status_code=status.HTTP_201_CREATED,
)
def add_participant(
    session_id: int,
    payload: schemas.LearningParticipantIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.add_participant(
        db, current_user, session_id, user_id=payload.user_id, role=payload.role
    )


@router.delete("/{session_id}/participants/{participant_id}", response_model=schemas.LearningParticipantOut)
def remove_participant(
    session_id: int,
    participant_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.remove_participant(db, current_user, session_id, participant_id)


# ---- Objectives ----

@router.get("/{session_id}/objectives", response_model=List[schemas.LearningObjectiveOut])
def list_objectives(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, current_user, session)
    return sorted(session.objectives or [], key=lambda o: o.sequence)


@router.post(
    "/{session_id}/objectives",
    response_model=schemas.LearningObjectiveOut,
    status_code=status.HTTP_201_CREATED,
)
def add_objective(
    session_id: int,
    payload: schemas.LearningObjectiveIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.add_objective(
        db,
        current_user,
        session_id,
        statement=payload.statement,
        sequence=payload.sequence,
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        subtopic_id=payload.subtopic_id,
        concept_tag=payload.concept_tag,
    )


@router.delete("/{session_id}/objectives/{objective_id}")
def delete_objective(
    session_id: int,
    objective_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.delete_objective(db, current_user, session_id, objective_id)


# ---- Activities ----

@router.get("/{session_id}/activities", response_model=List[schemas.LearningActivityOut])
def list_activities(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = ls.get_session(db, session_id)
    ls.require_view_session(db, current_user, session)
    return sorted(session.activities or [], key=lambda a: a.sequence)


@router.post(
    "/{session_id}/activities",
    response_model=schemas.LearningActivityOut,
    status_code=status.HTTP_201_CREATED,
)
def add_activity(
    session_id: int,
    payload: schemas.LearningActivityIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.add_activity(
        db,
        current_user,
        session_id,
        activity_type=payload.activity_type,
        title=payload.title,
        description=payload.description,
        sequence=payload.sequence,
        scope=payload.scope,
        participant_id=payload.participant_id,
        payload=payload.payload,
        assessment_id=payload.assessment_id,
    )


@router.patch("/{session_id}/activities/{activity_id}", response_model=schemas.LearningActivityOut)
def update_activity(
    session_id: int,
    activity_id: int,
    payload: schemas.LearningActivityUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    kwargs = {}
    if "title" in data:
        kwargs["title"] = data["title"]
    if "description" in data:
        kwargs["description"] = data["description"]
    if "sequence" in data:
        kwargs["sequence"] = data["sequence"]
    if "status" in data:
        kwargs["status_value"] = data["status"]
    if "payload" in data:
        kwargs["payload"] = data["payload"]
    return ls.update_activity(db, current_user, session_id, activity_id, **kwargs)


@router.delete("/{session_id}/activities/{activity_id}")
def delete_activity(
    session_id: int,
    activity_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.delete_activity(db, current_user, session_id, activity_id)


# ---- Evidence ----

@router.get("/{session_id}/evidence", response_model=List[schemas.LearningEvidenceOut])
def get_evidence(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.list_evidence(db, current_user, session_id)


@router.post(
    "/{session_id}/evidence",
    response_model=schemas.LearningEvidenceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    session_id: int,
    payload: schemas.LearningEvidenceIn,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return ls.record_evidence(
        db,
        current_user,
        session_id=session_id,
        event_type=payload.event_type,
        user_id=payload.user_id,
        participant_id=payload.participant_id,
        activity_id=payload.activity_id,
        objective_id=payload.objective_id,
        payload=payload.payload,
    )
