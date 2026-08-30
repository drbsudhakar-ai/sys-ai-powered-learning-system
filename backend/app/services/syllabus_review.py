"""Versioned syllabus governance. No helper commits the caller's transaction."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from app import models
from app.academic_auth import is_admin, is_course_coordinator, is_subject_expert

LEVELS = ("subject", "unit", "topic", "subtopic")
MODELS = dict(zip(LEVELS, (models.Subject, models.Unit, models.Topic, models.Subtopic)))


def fingerprint(nodes):
    return hashlib.sha256(json.dumps(sorted(nodes, key=lambda n: n["key"]), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def manager(db, actor, course_id):
    return is_admin(actor) or is_course_coordinator(db, actor, course_id)


def course_scope(db, actor, course_id, *, write=False):
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if write and course.publication_status == "ARCHIVED":
        raise HTTPException(409, "Archived courses cannot accept syllabus changes")
    if manager(db, actor, course_id):
        return course, None
    ids = {x[0] for x in db.query(models.Subject.id).join(models.SubjectExpertAssignment).filter(
        models.Subject.course_id == course_id, models.SubjectExpertAssignment.faculty_id == actor.id).all()}
    if (actor.role or "").lower() == "faculty" and ids:
        return course, ids
    if not write and (actor.role or "").lower() == "student":
        from app.services.course_enrollments import has_learning_access
        if has_learning_access(db, actor.id, course_id):
            return course, None
    raise HTTPException(403, "Academic responsibility or active course enrollment is required")


def snapshot(db, course_id):
    nodes = []
    def add(obj, level, parent):
        nodes.append(dict(key=f"{level}:{obj.id}", level=level, parent=parent,
                          name=obj.name, description=obj.description or "", sequence=obj.sequence,
                          learning_outcome=(obj.learning_outcome or "") if level == "unit" else ""))
    for s in db.query(models.Subject).options(selectinload(models.Subject.units),
            selectinload(models.Subject.topics).selectinload(models.Topic.subtopics)).filter_by(course_id=course_id).order_by(models.Subject.id):
        add(s, "subject", None)
        for u in s.units:
            add(u, "unit", f"subject:{s.id}")
        for t in s.topics:
            if t.unit_id is None:
                raise HTTPException(409, "Legacy topics without a unit must be assigned to a unit before syllabus review")
            add(t, "topic", f"unit:{t.unit_id}")
            for st in t.subtopics:
                add(st, "subtopic", f"topic:{t.id}")
    return nodes


def subject_key(node, lookup):
    while node["level"] != "subject":
        node = lookup[node["parent"]]
    return node["key"]


def scoped(nodes, subject_ids):
    if subject_ids is None:
        return deepcopy(nodes)
    lookup = {n["key"]: n for n in nodes}
    allowed = {f"subject:{sid}" for sid in subject_ids}
    return [deepcopy(n) for n in nodes if subject_key(n, lookup) in allowed]


def changes(before, after):
    old = {n["key"]: n for n in before}
    return [dict(kind="Added" if n["key"] not in old else "Updated", before=old.get(n["key"]), after=n)
            for n in after if old.get(n["key"]) != n]


def validate_nodes(nodes, baseline, *, faculty=False):
    errors, lookup = [], {}
    for index, raw in enumerate(nodes, 1):
        n = dict(raw)
        if n["key"] in lookup:
            errors.append(f"Item {index}: duplicate SYS identifier")
        lookup[n["key"]] = n
        if not n["name"].strip():
            errors.append(f"Item {index}: name is required")
        n["name"] = n["name"].strip()
        n["description"] = n["description"].strip()
        n["learning_outcome"] = n["learning_outcome"].strip()
        if n["level"] != "unit" and n["learning_outcome"]:
            errors.append(f"{n['name']}: learning outcome belongs on the unit")
    old = {n["key"]: n for n in baseline}
    for key, n in lookup.items():
        level = n["level"]
        if key not in old and not re.fullmatch(r"new:[a-zA-Z0-9_-]{1,80}", key):
            errors.append(f"{n['name']}: unknown or damaged SYS identifier")
        if level == "subject":
            valid_parent = n["parent"] is None
        else:
            parent = lookup.get(n["parent"])
            valid_parent = parent and parent["level"] == LEVELS[LEVELS.index(level)-1]
        if not valid_parent:
            errors.append(f"{n['name']}: missing or invalid parent")
        if key in old and (old[key]["level"] != level or old[key]["parent"] != n["parent"]):
            errors.append(f"{n['name']}: moving existing items between parents is not supported; retain its parent")
        if faculty and level in ("subject", "unit") and old.get(key) != n:
            errors.append(f"{n['name']}: only coordinator/admin may change subjects or units")
    if set(old) - set(lookup):
        errors.append("Existing items cannot be deleted in a proposal. Request retirement separately from your coordinator.")
    seen_names, seen_order = set(), set()
    old_order = {}
    for n in baseline:
        group = (n["level"], n["parent"], n["sequence"])
        old_order.setdefault(group, set()).add(n["key"])
    new_order = {}
    for n in lookup.values():
        new_order.setdefault((n["level"], n["parent"], n["sequence"]), set()).add(n["key"])
    for n in lookup.values():
        group = (n["level"], n["parent"])
        name = (*group, n["name"].casefold())
        order = (*group, n["sequence"])
        if name in seen_names:
            errors.append(f"{n['name']}: duplicate name under the same parent")
        # Legacy ties may remain unchanged; new/edited ties must be corrected.
        peers = new_order[order]
        if order in seen_order and peers != old_order.get(order):
            errors.append(f"{n['name']}: duplicate order {n['sequence']} under the same parent")
        seen_names.add(name); seen_order.add(order)
    if errors:
        raise HTTPException(422, {"errors": errors[:60]})
    return list(lookup.values())


def audit(db, actor, proposal, action, details=None):
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action=f"syllabus.{action}", target_type="syllabus_review",
        target_id=proposal.id, summary=f"Syllabus review {proposal.id}: {action}",
        details={"course_id": proposal.course_id, "review_version": proposal.version, **(details or {})}))


def notify(db, proposal, event, users, message):
    from app.services.notifications import enqueue_targeted_event
    return enqueue_targeted_event(db, event=event, users=users, course_id=proposal.course_id,
        title="SYS syllabus review", message=message,
        link_path=f"/courses/{proposal.course_id}/syllabus-review?review={proposal.id}",
        payload={"review_id": proposal.id})


def coordinators(db, course_id):
    return db.query(models.User).join(models.FacultyCourseAssignment,
        models.FacultyCourseAssignment.faculty_id == models.User.id).filter(
        models.FacultyCourseAssignment.course_id == course_id, models.User.is_active.is_(True),
        models.User.account_status == "ACTIVE").all()


def approve(db, actor, course, proposal, comment, *, subject_workflow=False):
    if not subject_workflow:
        raise HTTPException(409, "Use subject-wise expert review and final approval before publishing")
    if not manager(db, actor, course.id):
        raise HTTPException(403, "Course-coordinator approval is required")
    if proposal.status != "SUBMITTED":
        raise HTTPException(409, "Only a submitted proposal can be approved")
    if proposal.subject_id and course.syllabus_revision == 0:
        raise HTTPException(409, "Approve the initial whole-course baseline before approving subject-only updates")
    author = db.get(models.User, proposal.author_id)
    if not author or not author.is_active or author.account_status != "ACTIVE":
        raise HTTPException(409, "Proposal author is no longer active")
    if proposal.subject_id and not (manager(db, author, course.id) or is_subject_expert(db, author, proposal.subject_id)):
        raise HTTPException(409, "Faculty responsibility has changed; ask the assigned faculty to prepare a new review")
    if not proposal.subject_id and not manager(db, author, course.id):
        raise HTTPException(409, "The author no longer coordinates this course")
    if proposal.subject_id and actor.id == proposal.author_id and not is_admin(actor):
        raise HTTPException(403, "A faculty proposal cannot be self-approved")
    current = snapshot(db, course.id)
    if fingerprint(current) != proposal.base_hash or course.syllabus_revision != proposal.base_revision:
        raise HTTPException(409, "Approved syllabus changed. Create a fresh review and reconcile this proposal; nothing was applied.")
    baseline = scoped(current, {proposal.subject_id}) if proposal.subject_id else current
    desired = validate_nodes(proposal.proposed_nodes, baseline, faculty=bool(proposal.subject_id))
    review_claim = db.execute(update(models.SyllabusReview).where(models.SyllabusReview.id == proposal.id,
        models.SyllabusReview.version == proposal.version, models.SyllabusReview.status == "SUBMITTED"
        ).values(version=proposal.version+1), execution_options={"synchronize_session": False})
    if review_claim.rowcount != 1:
        raise HTTPException(409, "This proposal was changed or withdrawn; reload before approving")
    db.refresh(proposal)
    # Compare-and-swap protects SQLite and PostgreSQL even if row locks are unavailable.
    result = db.execute(update(models.Course).where(models.Course.id == course.id,
        models.Course.syllabus_revision == proposal.base_revision).values(syllabus_revision=proposal.base_revision+1),
        execution_options={"synchronize_session": False})
    if result.rowcount != 1:
        raise HTTPException(409, "A newer approval already exists; reload before continuing")
    ids = {n["key"]: int(n["key"].split(":")[1]) for n in current}
    objects = {}
    for level, model in MODELS.items():
        existing_ids = [ids[n["key"]] for n in desired if n["level"] == level and n["key"] in ids]
        for obj in db.query(model).filter(model.id.in_(existing_ids)).all():
            objects[f"{level}:{obj.id}"] = obj
    # Temporary names permit safe sibling name swaps despite unique DB constraints.
    for n in desired:
        if n["key"] in ids and n["level"] in ("subject", "unit"):
            obj = objects[n["key"]]
            if obj.name != n["name"]:
                obj.name = f"__SYS_REVIEW_{uuid4().hex}"
    db.flush()
    for level in LEVELS:
        level_nodes = [n for n in desired if n["level"] == level]
        for n in level_nodes:
            obj = objects.get(n["key"]) or MODELS[level]()
            if n["key"] not in ids:
                if level == "subject": obj.course_id = course.id
                elif level == "unit": obj.subject_id = ids[n["parent"]]
                elif level == "topic":
                    obj.unit_id = ids[n["parent"]]
                    obj.subject_id = objects[n["parent"]].subject_id
                else: obj.topic_id = ids[n["parent"]]
                db.add(obj)
            obj.name, obj.description, obj.sequence = n["name"], n["description"] or None, n["sequence"]
            if level == "unit": obj.learning_outcome = n["learning_outcome"] or None
            objects[n["key"]] = obj
        db.flush()
        for n in level_nodes: ids[n["key"]] = objects[n["key"]].id
    db.expire_all()
    approved = snapshot(db, course.id)
    # Preserve lesson payloads and completion evidence; mark affected saved lessons
    # for academic review without spending AI quota or rewriting past sessions.
    changed = changes(proposal.base_nodes, desired)
    content_changes = [c for c in changed if c["before"] is None or any(
        c["before"][field] != c["after"][field] for field in ("name", "description", "learning_outcome"))]
    lookup = {n["key"]: n for n in desired}
    affected_subjects = {ids[subject_key(c["after"], lookup)] for c in content_changes}
    if affected_subjects:
        for activity in db.query(models.LearningSessionActivity).join(models.LearningSession).filter(
            models.LearningSession.course_id == course.id, models.LearningSession.subject_id.in_(affected_subjects),
            models.LearningSessionActivity.activity_type == "LECTURE").all():
            activity.payload = {**(activity.payload or {}), "syllabus_review_required": True,
                "syllabus_revision": proposal.base_revision+1}
    revision = models.SyllabusRevision(course_id=course.id, number=proposal.base_revision+1,
        nodes=approved, approved_by=actor.id, review_id=proposal.id, summary=proposal.summary,
        course_title=course.title, programme_code=course.programme_code)
    db.add(revision)
    proposal.status, proposal.decision_comment = "APPROVED", comment
    proposal.decided_by, proposal.decided_at = actor.id, datetime.now(timezone.utc)
    audit(db, actor, proposal, "approved", {"revision": revision.number,
        "changes": changes(proposal.base_nodes, desired), "comment": comment,
        "administrative_override": is_admin(actor), "lesson_review_required": bool(changes(proposal.base_nodes, desired))})
    return notify(db, proposal, "SYLLABUS_REVIEW_DECIDED", [author],
        f"Your syllabus review was approved as revision {revision.number}. {comment}")


def guard_legacy_write(db, course_id):
    """Preserve compatibility setup, but never bypass an established approval trail."""
    if course_id:
        course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
        if course and (course.syllabus_revision > 0 or db.query(models.SyllabusReview.id).filter_by(course_id=course_id).first()):
            raise HTTPException(409, "Use the syllabus review workspace; direct edits cannot bypass approval")
