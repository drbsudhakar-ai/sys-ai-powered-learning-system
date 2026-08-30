"""Subject-scoped review state. Mutations share the course lock and caller transaction."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app import models
from app.services import syllabus_review as core

def branch(nodes, key):
    lookup = {n['key']: n for n in nodes}
    return [n for n in nodes if core.subject_key(n, lookup) == key]

def tasks(db, review):
    return db.query(models.SyllabusSubjectReview).filter_by(review_id=review.id).all()

def carry_approvals(db, review):
    previous = db.query(models.SyllabusRevision).filter_by(course_id=review.course_id, number=review.base_revision).first()
    if not previous: return
    old_tasks = db.query(models.SyllabusSubjectReview).filter_by(review_id=previous.review_id, status='APPROVED').all()
    for old in old_tasks:
        if not old.live_subject_id or not valid_reviewer(db, old): continue
        key = f'subject:{old.live_subject_id}'
        nodes = branch(review.proposed_nodes, key)
        if not nodes: continue
        db.add(models.SyllabusSubjectReview(review_id=review.id, subject_key=key, live_subject_id=old.live_subject_id,
            reviewer_id=old.reviewer_id, requested_by=old.requested_by, status='APPROVED', version=1,
            source_hash=core.fingerprint(nodes), source_nodes=nodes, proposed_nodes=nodes,
            comment=old.comment, decision_comment=old.decision_comment, requested_at=old.requested_at,
            recommended_at=old.recommended_at, approved_at=old.approved_at, approved_by=old.approved_by))

def valid_reviewer(db, task):
    user = db.get(models.User, task.reviewer_id) if task.reviewer_id else None
    from app.services.syllabus_configuration import assignable
    if not assignable(user) or user.account_status != 'ACTIVE':
        return False
    live_id = task.live_subject_id or (int(task.subject_key.split(':')[1]) if task.subject_key.startswith('subject:') else None)
    if live_id:
        return core.is_subject_expert(db, user, live_id)
    return True  # Explicit draft-subject assignment, later copied to SubjectExpertAssignment.

def ready(db, review):
    subjects = [n for n in review.proposed_nodes if n['level'] == 'subject']
    by_key = {t.subject_key: t for t in tasks(db, review)}
    return bool(subjects) and all(n['key'] in by_key and by_key[n['key']].status == 'APPROVED'
        and valid_reviewer(db, by_key[n['key']])
        and by_key[n['key']].source_hash == core.fingerprint(branch(review.proposed_nodes, n['key'])) for n in subjects)

def notify(db, review, task, users, message):
    from app.services.notifications import enqueue_targeted_event
    return enqueue_targeted_event(db, event='SYLLABUS_REVIEW_DECIDED', users=users,
        course_id=review.course_id, title='SYS subject syllabus review', message=message,
        link_path=f'/courses/{review.course_id}/syllabus/reviews?review={review.id}&subject={task.id}',
        payload={'review_id': review.id, 'subject_review_id': task.id})

def invalidate(db, actor, review, desired):
    notifications = []
    for task in tasks(db, review):
        if task.source_hash and task.source_hash != core.fingerprint(branch(desired, task.subject_key)):
            core.audit(db, actor, review, 'subject_review_invalidated', {'subject_key': task.subject_key,
                'previous_status': task.status, 'source_nodes': task.source_nodes, 'proposed_nodes': task.proposed_nodes})
            if task.reviewer_id:
                notifications.append(notify(db, review, task, [db.get(models.User, task.reviewer_id)], 'The syllabus changed. This review is cancelled; wait for a new request.'))
            task.status = 'NOT_REQUESTED'; task.version += 1
            task.source_hash = ''; task.approved_at = None; task.approved_by = None
    return notifications

def materialize(db, actor, course, review):
    if review.status == 'APPROVED': return
    if not ready(db, review): raise HTTPException(409, 'Every subject requires expert recommendation and final approval')
    review.status = 'SUBMITTED'
    review.summary = review.summary or 'Subject-wise expert review and final academic approval'
    db.flush()
    core.approve(db, actor, course, review, 'All subject reviews finally approved', subject_workflow=True)
    # Draft subjects become real subjects only after the complete approved version is applied.
    live = {s.name: s for s in db.query(models.Subject).filter_by(course_id=course.id)}
    for task in tasks(db, review):
        node = next(n for n in review.proposed_nodes if n['key'] == task.subject_key)
        subject = live[node['name']]
        task.live_subject_id = subject.id
        if not db.query(models.SubjectExpertAssignment).filter_by(subject_id=subject.id, faculty_id=task.reviewer_id).first():
            db.add(models.SubjectExpertAssignment(subject_id=subject.id, faculty_id=task.reviewer_id))
    db.flush()


def approve_task(db, actor, course, review, task, comment):
    """Apply one current expert recommendation as an administrator syllabus decision."""
    from app.academic_auth import is_admin
    if not is_admin(actor): raise HTTPException(403, 'Administrator final approval is required')
    if task.status != 'RECOMMENDED': raise HTTPException(409, 'Expert recommendation is required first')
    if not comment.strip(): raise HTTPException(422, 'Record the final decision comment')
    current = branch(review.proposed_nodes, task.subject_key)
    if task.source_hash != core.fingerprint(current): raise HTTPException(409, 'Subject changed; request a fresh review')
    if not valid_reviewer(db, task): raise HTTPException(409, 'Reviewer assignment is no longer active')
    desired = [n for n in review.proposed_nodes if n not in current] + task.proposed_nodes
    core.validate_nodes(desired, review.base_nodes)
    review.proposed_nodes = desired
    task.source_hash = core.fingerprint(task.proposed_nodes)
    task.status = 'APPROVED'; task.version += 1
    task.decision_comment = comment.strip(); task.approved_at = datetime.now(timezone.utc); task.approved_by = actor.id

def publication_ready(db, course):
    pending = db.query(models.SyllabusReview).filter(models.SyllabusReview.course_id == course.id,
        models.SyllabusReview.status.in_(['DRAFT', 'SUBMITTED', 'CHANGES_REQUESTED'])).all()
    if pending: return len(pending) == 1 and ready(db, pending[0])
    return course.syllabus_revision > 0

def finalize_for_publication(db, actor, course):
    if not course: raise HTTPException(404, 'Course not found')
    pending = db.query(models.SyllabusReview).filter(models.SyllabusReview.course_id == course.id,
        models.SyllabusReview.status.in_(['DRAFT', 'SUBMITTED', 'CHANGES_REQUESTED'])).all()
    if len(pending) > 1: raise HTTPException(409, 'Resolve competing syllabus drafts before publication')
    if pending: materialize(db, actor, course, pending[0])

def document_status(review, subject_tasks, published=False):
    if published: return 'APPROVED AND PUBLISHED'
    if review.status == 'APPROVED' or subject_tasks and all(t.status == 'APPROVED' for t in subject_tasks):
        return 'APPROVED - NOT YET PUBLISHED'
    states = {t.status for t in subject_tasks}
    if 'APPROVED' in states: return 'PARTIALLY APPROVED - NOT PUBLISHED'
    if states and states <= {'RECOMMENDED'}: return 'EXPERT REVIEW COMPLETED - FINAL APPROVAL PENDING'
    if states & {'IN_REVIEW', 'RETURNED', 'RECOMMENDED'}: return 'UNDER SUBJECT EXPERT REVIEW'
    return 'DRAFT - NOT APPROVED'
