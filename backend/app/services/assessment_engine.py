"""Assessment blueprint validation and question assembly."""

from __future__ import annotations

import random
from typing import List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.constants import (
    ASSESSMENT_CATEGORIES,
    ASSESSMENT_TYPES,
    DIFFICULTIES,
    MULTI_SUBJECT_TYPES,
    TYPE_TO_CATEGORY,
)


def validate_type_category(assessment_type: str, category: str | None) -> str:
    if assessment_type not in ASSESSMENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid assessment_type: {assessment_type}")
    expected = TYPE_TO_CATEGORY[assessment_type]
    if category and category not in ASSESSMENT_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category: {category}")
    if category and category != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Category {category} does not match type {assessment_type} (expected {expected})",
        )
    return expected


def validate_marking(marks_correct, marks_incorrect, marks_unanswered, duration_minutes, total_questions, total_marks):
    if duration_minutes is not None and duration_minutes <= 0:
        raise HTTPException(status_code=422, detail="duration_minutes must be positive")
    if total_questions is not None and total_questions <= 0:
        raise HTTPException(status_code=422, detail="total_questions must be positive")
    if total_marks is not None and total_marks <= 0:
        raise HTTPException(status_code=422, detail="total_marks must be positive")
    if marks_correct is not None and marks_correct < 0:
        raise HTTPException(status_code=422, detail="marks_correct cannot be negative")


def validate_blueprint(
    db: Session,
    assessment: models.Assessment,
    items: List[models.AssessmentBlueprintItem],
) -> List[str]:
    """Return list of validation errors (empty if ok)."""
    errors: List[str] = []
    if not items:
        errors.append("Blueprint is empty")
        return errors

    for item in items:
        if item.difficulty not in DIFFICULTIES:
            errors.append(f"Invalid difficulty: {item.difficulty}")
        if item.question_count <= 0:
            errors.append("Blueprint question_count must be positive")
        subject = db.query(models.Subject).filter(models.Subject.id == item.subject_id).first()
        if not subject:
            errors.append(f"Subject {item.subject_id} not found")
        elif subject.course_id and subject.course_id != assessment.course_id:
            errors.append(f"Subject {subject.name} does not belong to this course")
        if item.topic_id:
            topic = db.query(models.Topic).filter(models.Topic.id == item.topic_id).first()
            if not topic:
                errors.append(f"Topic {item.topic_id} not found")
            elif topic.subject_id != item.subject_id:
                errors.append(f"Topic {item.topic_id} does not belong to subject {item.subject_id}")

    blueprint_total = sum(i.question_count for i in items)
    if assessment.total_questions and blueprint_total != assessment.total_questions:
        errors.append(
            f"Blueprint total ({blueprint_total}) does not match total_questions ({assessment.total_questions})"
        )

    # Subject distribution consistency for multi-subject types
    if assessment.assessment_type in MULTI_SUBJECT_TYPES:
        subjects = {i.subject_id for i in items}
        if len(subjects) < 1:
            errors.append("Multi-subject assessments require at least one subject in blueprint")

    if assessment.assessment_type == "TOPIC_TEST":
        subjects = {i.subject_id for i in items}
        topics = {i.topic_id for i in items if i.topic_id}
        if len(subjects) > 1:
            errors.append("Topic Test blueprint must use a single subject")
        if assessment.topic_id and topics and assessment.topic_id not in topics:
            errors.append("Topic Test blueprint topics must match assessment topic")

    return errors


def eligible_questions(
    db: Session,
    *,
    course_id: int,
    subject_id: int,
    topic_id: int | None,
    subtopic_id: int | None,
    difficulty: str,
) -> List[models.Question]:
    q = db.query(models.Question).filter(
        models.Question.course_id == course_id,
        models.Question.subject_id == subject_id,
        models.Question.difficulty == difficulty,
        models.Question.status == "ACTIVE",
    )
    if topic_id is not None:
        q = q.filter(models.Question.topic_id == topic_id)
    if subtopic_id is not None:
        q = q.filter(models.Question.subtopic_id == subtopic_id)
    return q.all()


def assemble_questions(
    db: Session,
    assessment: models.Assessment,
    items: List[models.AssessmentBlueprintItem],
) -> Tuple[List[models.Question], List[str]]:
    """Select questions per blueprint. Returns (selected, errors).

    Grand/Final assessments use evidence-based Question Intelligence ranking.
    Other types use random sampling among eligible ACTIVE questions.
    """
    from app.services.selection_engine import select_for_blueprint_item

    errors = validate_blueprint(db, assessment, items)
    if errors:
        return [], errors

    evidence = (assessment.assessment_type or "") in ("GRAND_TEST", "FINAL_GRAND_TEST")
    selected: List[models.Question] = []
    used_ids: set[int] = set()

    for item in items:
        picks, item_errors = select_for_blueprint_item(
            db, assessment, item, used_ids, evidence_based=evidence
        )
        if item_errors:
            errors.extend(item_errors)
            continue
        for p in picks:
            used_ids.add(p.id)
            selected.append(p)

    return selected, errors
