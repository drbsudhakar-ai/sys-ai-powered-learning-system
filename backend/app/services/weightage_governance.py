"""Governance for independently reviewed academic weightages."""
from datetime import datetime, timezone
import hashlib
import json
from math import isclose

from fastapi import HTTPException
from app import models
from app.academic_auth import is_admin, is_course_coordinator, is_subject_expert


def _weighted(items):
    return bool(items) and all(item.get("weight_percent") is not None for item in items) and isclose(
        sum(item["weight_percent"] for item in items), 100.0, abs_tol=0.01
    )


def subject_complete(tree, subject_id):
    subjects = tree.get("subjects") or []
    subject = next((item for item in subjects if item["id"] == subject_id), None)
    if not subject or not _weighted(subjects) or not _weighted(subject["units"]):
        return False
    return all(
        _weighted(unit["topics"])
        and all(not topic["subtopics"] or _weighted(topic["subtopics"]) for topic in unit["topics"])
        for unit in subject["units"]
    )


def snapshot(tree, subject_id):
    subject = next((item for item in tree.get("subjects", []) if item["id"] == subject_id), None)
    if not subject:
        raise HTTPException(404, "Subject does not belong to this course")
    values = {
        "subject": [[item["id"], item.get("weight_percent")] for item in tree["subjects"]],
        "units": [[item["id"], item.get("weight_percent")] for item in subject["units"]],
        "topics": [[item["id"], item.get("weight_percent")] for unit in subject["units"] for item in unit["topics"]],
        "subtopics": [[item["id"], item.get("weight_percent")] for unit in subject["units"] for topic in unit["topics"] for item in topic["subtopics"]],
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def state(db, course_id, subject_id, *, create=False):
    row = db.query(models.SubjectWeightageApproval).filter_by(course_id=course_id, subject_id=subject_id).first()
    if not row and create:
        row = models.SubjectWeightageApproval(course_id=course_id, subject_id=subject_id)
        db.add(row); db.flush()
    return row


def invalidate(db, course, subject_ids):
    """Any saved weight change invalidates its approval and course confirmation."""
    course.coordinator_readiness_status = "PENDING"
    course.coordinator_confirmed_at = course.coordinator_confirmed_by = None
    for subject_id in subject_ids:
        row = state(db, course.id, subject_id, create=True)
        row.status = "DRAFT"; row.version += 1; row.snapshot_hash = ""
        row.recommended_by = row.recommended_at = row.approved_by = row.approved_at = None
        row.recommendation_comment = row.decision_comment = ""


def serialize(db, tree, subject):
    row = state(db, tree["course_id"], subject["id"])
    complete = subject_complete(tree, subject["id"])
    current_hash = snapshot(tree, subject["id"]) if complete else ""
    valid = bool(row and row.snapshot_hash and row.snapshot_hash == current_hash)
    status = row.status if valid or (row and row.status in {"DRAFT", "RETURNED"}) else "NOT_CONFIGURED" if not complete else "DRAFT"
    return {
        "subject_id": subject["id"], "subject_name": subject["name"], "complete": complete,
        "status": status, "version": row.version if row else 0,
        "recommendation_comment": row.recommendation_comment if row else "",
        "decision_comment": row.decision_comment if row else "",
    }


def all_recommended_or_approved(db, course, tree, syllabus_tasks):
    by_subject = {task.live_subject_id: task for task in syllabus_tasks if task.live_subject_id}
    for subject in tree.get("subjects", []):
        task = by_subject.get(subject["id"])
        weight = serialize(db, tree, subject)
        if not task or task.status not in {"RECOMMENDED", "APPROVED"} or weight["status"] not in {"RECOMMENDED", "APPROVED"}:
            return False
    return bool(tree.get("subjects"))


def all_approved(db, tree):
    return bool(tree.get("subjects")) and all(serialize(db, tree, subject)["status"] == "APPROVED" for subject in tree["subjects"])


def act(db, actor, course, subject, tree, action, version, comment):
    row = state(db, course.id, subject.id, create=True)
    if row.version != version:
        raise HTTPException(409, "Weightage approval changed. Reload and try again")
    complete = subject_complete(tree, subject.id)
    current_hash = snapshot(tree, subject.id) if complete else ""
    if action == "recommend":
        if not is_subject_expert(db, actor, subject.id):
            raise HTTPException(403, "Only an active assigned subject expert can recommend weightages")
        if not complete:
            raise HTTPException(409, "Complete every applicable weightage group at exactly 100% before recommendation")
        if not comment.strip():
            raise HTTPException(422, "Record the academic weightage recommendation")
        row.status = "RECOMMENDED"; row.snapshot_hash = current_hash
        row.recommendation_comment = comment.strip(); row.recommended_by = actor.id
        row.recommended_at = datetime.now(timezone.utc); row.approved_by = row.approved_at = None
    elif action == "approve":
        if not is_admin(actor): raise HTTPException(403, "Administrator final approval is required")
        if course.coordinator_readiness_status != "CONFIRMED": raise HTTPException(409, "Course Coordinator readiness confirmation is required first")
        if row.status != "RECOMMENDED" or row.snapshot_hash != current_hash:
            raise HTTPException(409, "A current Subject Expert weightage recommendation is required")
        row.status = "APPROVED"; row.decision_comment = comment.strip()
        row.approved_by = actor.id; row.approved_at = datetime.now(timezone.utc)
    elif action == "return":
        if not (is_admin(actor) or is_course_coordinator(db, actor, course.id)):
            raise HTTPException(403, "Administrator or assigned Course Coordinator required")
        if row.status != "RECOMMENDED": raise HTTPException(409, "Only recommended weightages can be returned")
        if not comment.strip(): raise HTTPException(422, "Record the required changes")
        row.status = "RETURNED"; row.decision_comment = comment.strip()
        course.coordinator_readiness_status = "PENDING"
        course.coordinator_confirmed_at = course.coordinator_confirmed_by = None
    else:
        raise HTTPException(422, "Unsupported weightage governance action")
    row.version += 1
    return row
