"""Read-only faculty projection for saved, not-yet-materialized syllabus work."""

from app import models
from app.services import syllabus_review, syllabus_subjects


PENDING_REVIEW_STATUSES = ("DRAFT", "CHANGES_REQUESTED")


def latest_pending_review(db, course_id):
    return (
        db.query(models.SyllabusReview)
        .filter(
            models.SyllabusReview.course_id == course_id,
            models.SyllabusReview.subject_id.is_(None),
            models.SyllabusReview.status.in_(PENDING_REVIEW_STATUSES),
        )
        .order_by(models.SyllabusReview.id.desc())
        .first()
    )


def faculty_draft_assignments(db, faculty_id):
    """Return unique saved subject assignments that do not yet have live rows."""
    rows = (
        db.query(models.SyllabusSubjectReview, models.SyllabusReview, models.Course)
        .join(models.SyllabusReview, models.SyllabusReview.id == models.SyllabusSubjectReview.review_id)
        .join(models.Course, models.Course.id == models.SyllabusReview.course_id)
        .filter(
            models.SyllabusSubjectReview.reviewer_id == faculty_id,
            models.SyllabusReview.subject_id.is_(None),
            models.SyllabusReview.status.in_(PENDING_REVIEW_STATUSES),
        )
        .order_by(models.SyllabusReview.id.desc(), models.SyllabusSubjectReview.id.desc())
        .all()
    )
    result, seen = [], set()
    for task, review, course in rows:
        identity = (course.id, task.subject_key)
        if identity in seen:
            continue
        node = next((item for item in review.proposed_nodes if item["key"] == task.subject_key and item["level"] == "subject"), None)
        if not node:
            continue
        # A live assignment is already represented by SubjectExpertAssignment.
        live_id = task.live_subject_id or (int(task.subject_key.split(":", 1)[1]) if task.subject_key.startswith("subject:") else None)
        if live_id and db.query(models.SubjectExpertAssignment.id).filter_by(subject_id=live_id, faculty_id=faculty_id).first():
            continue
        seen.add(identity)
        result.append({
            "id": f"draft:{task.id}",
            "name": node["name"],
            "course_id": course.id,
            "course_title": course.title,
            "responsibility": "SUBJECT_EXPERT",
            "review_status": task.status,
            "subject_key": task.subject_key,
            "review_id": review.id,
            "review_task_id": task.id,
        })
    return result


def _tree(nodes, tasks):
    by_parent = {}
    for node in nodes:
        by_parent.setdefault(node.get("parent"), []).append(node)
    for children in by_parent.values():
        children.sort(key=lambda item: (item.get("sequence", 1), item.get("name", "").casefold()))
    task_by_key = {task.subject_key: task for task in tasks}

    subjects = []
    for subject in by_parent.get(None, []):
        task = task_by_key.get(subject["key"])
        reviewer = task and task.reviewer_id and task.reviewer_id
        experts = []
        if reviewer:
            # The caller supplies ORM-backed tasks, so the user lookup happens in workspace_projection.
            experts.append({"id": reviewer, "name": None})
        units = []
        for unit in by_parent.get(subject["key"], []):
            topics = []
            for topic in by_parent.get(unit["key"], []):
                subtopics = [
                    {
                        "id": child["key"], "name": child["name"],
                        "description": child.get("description") or "", "weight_percent": None,
                        "is_draft": True,
                    }
                    for child in by_parent.get(topic["key"], [])
                ]
                topics.append({
                    "id": topic["key"], "name": topic["name"],
                    "description": topic.get("description") or "", "weight_percent": None,
                    "subtopics": subtopics, "is_draft": True,
                })
            units.append({
                "id": unit["key"], "name": unit["name"], "sequence": unit.get("sequence", 1),
                "description": unit.get("description") or "", "learning_outcome": unit.get("learning_outcome") or "",
                "weight_percent": None, "topics": topics, "is_draft": True,
            })
        subjects.append({
            "id": subject["key"], "name": subject["name"], "description": subject.get("description") or "",
            "weight_percent": None, "experts": experts, "units": units, "is_draft": True,
            "review_status": task.status if task else "NOT_REQUESTED",
            "review_task_id": task.id if task else None,
        })
    return subjects


def workspace_projection(db, course, faculty, *, coordinator):
    """Return the authorized saved draft tree, or None when no draft applies."""
    review = latest_pending_review(db, course.id)
    if not review:
        return None
    tasks = syllabus_subjects.tasks(db, review)
    if coordinator:
        nodes, visible_tasks = review.proposed_nodes, tasks
    else:
        visible_tasks = [task for task in tasks if task.reviewer_id == faculty.id and syllabus_subjects.valid_reviewer(db, task)]
        keys = {task.subject_key for task in visible_tasks}
        lookup = {node["key"]: node for node in review.proposed_nodes}
        nodes = [node for node in review.proposed_nodes if syllabus_review.subject_key(node, lookup) in keys]
    if not nodes:
        return None
    tree = _tree(nodes, visible_tasks)
    names = {user.id: user.name for user in db.query(models.User).filter(models.User.id.in_({t.reviewer_id for t in visible_tasks if t.reviewer_id})).all()}
    for subject in tree:
        task = next((item for item in visible_tasks if item.subject_key == subject["id"]), None)
        subject["assigned_to_actor"] = bool(task and task.reviewer_id == faculty.id)
        for expert in subject["experts"]:
            expert["name"] = names.get(expert["id"], "Assigned subject expert")
    return {
        "review_id": review.id,
        "review_version": review.version,
        "status": "UNDER_REVIEW",
        "is_draft": True,
        "subjects": tree,
        "subject_count": len(tree),
        "unit_count": sum(len(subject["units"]) for subject in tree),
        "topic_count": sum(len(unit["topics"]) for subject in tree for unit in subject["units"]),
    }
