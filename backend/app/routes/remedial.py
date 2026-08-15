"""P0-014 Remedial Learning APIs — thin HTTP over remedial service."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import models, schemas, database
from app.routes.auth import get_current_user
from app.services import remedial as rem

router = APIRouter(prefix="/remedial", tags=["Remedial Learning"])


@router.get("/courses/{course_id}/gaps")
def list_eligible_gaps(
    course_id: int,
    student_id: Optional[int] = Query(None),
    min_severity: Optional[str] = Query("moderate"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.list_eligible_gaps(
        db,
        current_user,
        course_id=course_id,
        student_id=student_id,
        min_severity=min_severity,
    )


@router.get("/courses/{course_id}/gaps/prioritized")
def prioritized_gaps(
    course_id: int,
    student_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    gaps = rem.list_eligible_gaps(
        db, current_user, course_id=course_id, student_id=student_id, min_severity="low"
    )
    return rem.prioritize_student_gaps(gaps)


@router.post("/courses/{course_id}/proposals")
def propose_groups(
    course_id: int,
    persist: bool = Query(True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.propose_remedial_groups(db, current_user, course_id=course_id, persist=persist)


@router.get("/groups")
def list_groups(
    course_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.list_groups(db, current_user, course_id=course_id, status_filter=status_filter)


@router.get("/groups/{group_id}")
def get_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.get_group(db, current_user, group_id)


@router.post("/groups/{group_id}/activate")
def activate_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.activate_group(db, current_user, group_id)


@router.post("/groups/{group_id}/transition")
def transition_group(
    group_id: int,
    payload: schemas.RemedialStatusChange,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    g = rem.transition_group_status(db, current_user, group_id, payload.status)
    return rem.group_to_dict(db, g, include_members=True)


@router.post("/groups/{group_id}/intervention", status_code=status.HTTP_201_CREATED)
def create_group_plan(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    row = rem.create_group_intervention(db, current_user, group_id=group_id)
    return rem.intervention_to_dict(row)


@router.post("/interventions/individual", status_code=status.HTTP_201_CREATED)
def create_individual(
    payload: schemas.RemedialIndividualCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    row = rem.create_individual_intervention(
        db,
        current_user,
        course_id=payload.course_id,
        learning_gap_id=payload.learning_gap_id,
    )
    return rem.intervention_to_dict(row)


@router.post("/interventions/{intervention_id}/activate")
def activate_individual(
    intervention_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    row = rem.activate_individual_intervention(db, current_user, intervention_id)
    return rem.intervention_to_dict(row)


@router.get("/interventions")
def list_interventions(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.list_interventions_for_user(db, current_user, course_id=course_id)


@router.get("/interventions/{intervention_id}")
def get_intervention(
    intervention_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    return rem.get_intervention(db, current_user, intervention_id)


@router.patch("/interventions/{intervention_id}")
def patch_intervention(
    intervention_id: int,
    payload: schemas.RemedialInterventionUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    row = rem.update_intervention_status(
        db,
        current_user,
        intervention_id,
        status_value=data.get("status"),
        outcome=data.get("outcome"),
        reassessment_required=data.get("reassessment_required"),
        reassessment_completed=data.get("reassessment_completed"),
    )
    return rem.intervention_to_dict(row)


@router.get("/me")
def my_remedial(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Student-facing assignments + groups (no peer performance details)."""
    return {
        "interventions": rem.list_interventions_for_user(db, current_user, course_id=course_id),
        "groups": rem.list_groups(db, current_user, course_id=course_id),
    }
