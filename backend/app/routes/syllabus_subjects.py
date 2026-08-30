"""Requested subject reviews, guarded reset, and version-aware review PDFs."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from sqlalchemy import update
from app import database, models
from app.routes.auth import get_current_user
from app.routes.syllabus_review import claim, serialize, dispatch_later
from app.services import syllabus_review as core, syllabus_subjects as service
from app.syllabus_schemas import SubjectReviewAction, ResetSyllabus
from app.services.syllabus_configuration import assignable

router = APIRouter(prefix='/courses/{course_id}/syllabus-review', tags=['Subject syllabus review'])

def access(db, actor, course_id, review_id, write=False):
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    row = db.query(models.SyllabusReview).filter_by(id=review_id, course_id=course_id).with_for_update().first()
    if not course or not row: raise HTTPException(404, 'Syllabus not found')
    manager = core.manager(db, actor, course_id)
    assigned = [t for t in service.tasks(db, row) if t.reviewer_id == actor.id and service.valid_reviewer(db, t)]
    if not manager and not assigned: raise HTTPException(403, 'Assigned subject reviewer or course manager required')
    if write and course.publication_status == 'ARCHIVED': raise HTTPException(409, 'Archived course is read-only')
    return course, row, manager, assigned

def task_data(db, task):
    value = {k: getattr(task, k) for k in ('id', 'subject_key', 'reviewer_id', 'status', 'version', 'comment',
        'decision_comment', 'requested_at', 'recommended_at', 'approved_at', 'source_nodes', 'proposed_nodes')}
    for field, identifier in [('reviewer_name', task.reviewer_id), ('approver_name', task.approved_by)]:
        user = db.get(models.User, identifier) if identifier else None
        value[field] = user.name if user else None
    value['assignment_valid'] = service.valid_reviewer(db, task)
    return value

@router.get('/subject-dashboard')
def dashboard(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course = db.get(models.Course, course_id)
    if not course: raise HTTPException(404, 'Course not found')
    manager = core.manager(db, actor, course_id)
    rows = db.query(models.SyllabusReview).filter_by(course_id=course_id).order_by(models.SyllabusReview.id.desc()).all()
    result = []
    for row in rows:
        assigned = [t for t in service.tasks(db, row) if manager or (t.reviewer_id == actor.id and service.valid_reviewer(db, t))]
        if not manager and not assigned: continue
        if row.subject_id: continue  # Legacy proposals remain retained, not mixed into new requests.
        subjects = [n for n in row.proposed_nodes if n['level'] == 'subject' and (manager or any(t.subject_key == n['key'] for t in assigned))]
        subjects = [{**n, 'eligible_reviewers': [x.faculty_id for x in db.query(models.SubjectExpertAssignment).filter_by(subject_id=int(n['key'].split(':')[1]))] if n['key'].startswith('subject:') else None} for n in subjects]
        result.append(dict(id=row.id, version=row.version, status=row.status, subjects=subjects,
            tasks=[task_data(db, t) for t in assigned if t.subject_key in {s['key'] for s in subjects}], all_approved=service.ready(db, row),
            history=[dict(action=a.action, at=a.created_at, details=a.details) for a in db.query(models.AdminAuditLog).filter_by(target_type='syllabus_review', target_id=row.id).order_by(models.AdminAuditLog.id) if manager or (a.details or {}).get('subject_key') in {t.subject_key for t in assigned}]))
    if not manager and not result: raise HTTPException(403, 'No assigned syllabus review')
    faculty = [f for f in db.query(models.User).filter(models.User.role == 'faculty').order_by(models.User.name, models.User.id) if assignable(f)] if manager else []
    return dict(course_title=course.title, course_code=course.programme_code, actor_id=actor.id,
        can_manage=manager, archived=course.publication_status == 'ARCHIVED', reviews=result,
        faculty=[dict(id=f.id, name=f.name, employee_code=f.employee_code, department=f.department,
                      account_status=f.account_status) for f in faculty], revision=course.syllabus_revision,
        revisions=[dict(number=v.number, approved_at=v.created_at, published_at=v.published_at, summary=v.summary) for v in db.query(models.SyllabusRevision).filter_by(course_id=course_id).order_by(models.SyllabusRevision.number.desc())] if manager else [])

@router.post('/reviews/{review_id}/subject-action')
def act(course_id: int, review_id: int, body: SubjectReviewAction, background: BackgroundTasks,
        db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, row, manager, assigned = access(db, actor, course_id, review_id, True)
    if row.status not in {'DRAFT', 'CHANGES_REQUESTED'}: raise HTTPException(409, 'This syllabus version is not editable')
    task = db.query(models.SyllabusSubjectReview).filter_by(review_id=row.id, subject_key=body.subject_key).first()
    current = service.branch(row.proposed_nodes, body.subject_key)
    if not current: raise HTTPException(404, 'Subject not found in saved syllabus')
    if body.action in {'assign', 'unassign', 'request'}:
        if not manager: raise HTTPException(403, 'Only admin or coordinator may assign and request reviews')
        if row.version != body.version: raise HTTPException(409, 'Syllabus changed. Reload before requesting review')
        if not task:
            task = models.SyllabusSubjectReview(review_id=row.id, subject_key=body.subject_key)
            db.add(task); db.flush()
        if body.action in {'assign', 'unassign'}:
            if task.status not in {'NOT_REQUESTED', 'CANCELLED'}: raise HTTPException(409, 'Finish or invalidate the current request before reassignment')
            if body.action == 'assign':
                person = db.get(models.User, body.reviewer_id) if body.reviewer_id else None
                if not assignable(person): raise HTTPException(422, 'Select an active faculty master record; disabled or inactive faculty cannot be assigned')
                # Existing subjects share academic ownership immediately. New subject
                # keys use the same saved assignment until approval creates live IDs.
                if body.subject_key.startswith('subject:'):
                    subject_id = int(body.subject_key.split(':')[1])
                    subject = db.get(models.Subject, subject_id)
                    if not subject or subject.course_id != course_id: raise HTTPException(422, 'Subject does not belong to this course')
                    if not db.query(models.SubjectExpertAssignment).filter_by(subject_id=subject_id, faculty_id=person.id).first():
                        db.add(models.SubjectExpertAssignment(subject_id=subject_id, faculty_id=person.id))
                        db.flush()
                task.reviewer_id = person.id
            else:
                if body.subject_key.startswith('subject:'): raise HTTPException(409, 'Remove existing subject responsibility from Academic Responsibilities')
                task.reviewer_id = None
        else:
            if task.status not in {'NOT_REQUESTED', 'CANCELLED'}: raise HTTPException(409, 'Review already requested')
            if not task.reviewer_id and body.subject_key.startswith('subject:'):
                assigned_ids = [a.faculty_id for a in db.query(models.SubjectExpertAssignment).filter_by(subject_id=int(body.subject_key.split(':')[1]))]
                eligible = [identifier for identifier in assigned_ids
                            if assignable(db.get(models.User, identifier)) and db.get(models.User, identifier).account_status == 'ACTIVE']
                if len(eligible) == 1:
                    task.reviewer_id = eligible[0]
            if not service.valid_reviewer(db, task): raise HTTPException(422, 'Assign a subject expert with an active registered account before requesting review')
            task.source_nodes = current; task.proposed_nodes = current; task.source_hash = core.fingerprint(current)
            task.status = 'IN_REVIEW'; task.requested_by = actor.id; task.requested_at = datetime.now(timezone.utc)
            task.recommended_at = task.approved_at = None; task.approved_by = None; task.comment = ''; task.decision_comment = ''
        task.version += 1
        claim(db, row, row.version)
    else:
        if not task or task.version != body.version: raise HTTPException(409, 'Subject review changed. Reload and try again')
        claimed = db.execute(update(models.SyllabusSubjectReview).where(models.SyllabusSubjectReview.id == task.id,
            models.SyllabusSubjectReview.version == body.version).values(version=body.version+1), execution_options={'synchronize_session': False})
        if claimed.rowcount != 1: raise HTTPException(409, 'Subject review changed. Reload and try again')
        db.refresh(task)
        if task.source_hash != core.fingerprint(current): raise HTTPException(409, 'Subject changed; request a fresh review')
        if not service.valid_reviewer(db, task): raise HTTPException(409, 'Reviewer assignment is no longer active')
        if body.action in {'save', 'recommend'}:
            if task.reviewer_id != actor.id: raise HTTPException(403, 'Only the assigned subject expert can recommend approval')
            if task.status not in {'IN_REVIEW', 'RETURNED'}: raise HTTPException(409, 'Review is not awaiting expert input')
            if body.nodes is not None:
                task.proposed_nodes = core.validate_nodes([n.model_dump() for n in body.nodes], task.source_nodes, faculty=True)
            task.comment = body.comment.strip()
            if body.action == 'recommend':
                if not task.comment: raise HTTPException(422, 'Record your academic recommendation')
                task.status = 'RECOMMENDED'; task.recommended_at = datetime.now(timezone.utc)
        else:
            if not manager: raise HTTPException(403, 'Final decision requires admin or assigned course coordinator')
            if actor.id == task.reviewer_id: raise HTTPException(403, 'Final approval must be by a different person from the subject reviewer')
            if task.status != 'RECOMMENDED': raise HTTPException(409, 'Expert recommendation is required first')
            if not body.comment.strip(): raise HTTPException(422, 'Record the final decision comment')
            task.decision_comment = body.comment.strip()
            if body.action == 'return': task.status = 'RETURNED'
            else:
                desired = [n for n in row.proposed_nodes if n not in current] + task.proposed_nodes
                core.validate_nodes(desired, row.base_nodes)
                claim(db, row, row.version); row.proposed_nodes = desired
                task.source_hash = core.fingerprint(task.proposed_nodes)
                task.status = 'APPROVED'; task.approved_at = datetime.now(timezone.utc); task.approved_by = actor.id
    core.audit(db, actor, row, 'subject_' + body.action, {'subject_key': task.subject_key, 'task_id': task.id,
        'status': task.status, 'comment': body.comment, 'reviewer_id': task.reviewer_id,
        'changes': core.changes(task.source_nodes or [], task.proposed_nodes or [])})
    recipients = [db.get(models.User, task.reviewer_id)] if body.action in {'request', 'return', 'approve'} else core.coordinators(db, course_id) + ([db.get(models.User, task.requested_by)] if task.requested_by else [])
    notification = None
    if body.action not in {'assign', 'unassign', 'save'}:
        notification = service.notify(db, row, task, recipients, f"{current[0]['name']}: {task.status.replace('_', ' ').lower()}. {body.comment}")
    db.flush()
    if service.ready(db, row) and course.publication_status != 'PUBLISHED': service.materialize(db, actor, course, row)
    db.commit()
    if notification: background.add_task(dispatch_later, notification)
    return {'ok': True, 'status': task.status}

@router.post('/reviews/{review_id}/reset')
def reset(course_id: int, review_id: int, body: ResetSyllabus, background: BackgroundTasks,
          db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, row, manager, _ = access(db, actor, course_id, review_id, True)
    if not manager: raise HTTPException(403, 'Admin or assigned coordinator required')
    if body.course_code != course.programme_code or not body.reason.strip(): raise HTTPException(422, 'Enter the exact course code and reason')
    rows = service.tasks(db, row)
    if course.syllabus_revision or course.publication_status == 'PUBLISHED' or row.status == 'APPROVED' or any(t.status == 'APPROVED' for t in rows):
        raise HTTPException(409, 'Approved or published content cannot be cleared')
    if core.snapshot(db, course_id) or db.query(models.LearningSession.id).filter_by(course_id=course_id).first() or db.query(models.Assessment.id).filter_by(course_id=course_id).first():
        raise HTTPException(409, 'Existing academic records prevent clearing. Only an unattached working syllabus can be reset')
    active = [t for t in rows if t.status in {'IN_REVIEW', 'RETURNED', 'RECOMMENDED'}]
    if active and not body.cancel_requests: raise HTTPException(409, 'Confirm cancellation of active review requests')
    claim(db, row, body.version)
    core.audit(db, actor, row, 'reset_snapshot', {'nodes': row.proposed_nodes, 'reason': body.reason, 'cancelled_tasks': [t.id for t in active]})
    notification_ids = []
    for task in rows:
        if task in active:
            notification_ids.append(service.notify(db, row, task, [db.get(models.User, task.reviewer_id)], 'Review cancelled: the unapproved syllabus was cleared by the course manager.'))
        task.status = 'CANCELLED'; task.version += 1
    row.proposed_nodes = []; row.status = 'DRAFT'; row.summary = ''
    db.commit()
    for identifier in notification_ids:
        if identifier: background.add_task(dispatch_later, identifier)
    return serialize(db, row, full=True)

@router.get('/reviews/{review_id}/syllabus.pdf')
def pdf(course_id: int, review_id: int, subject_key: str | None = None,
        db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, row, manager, assigned = access(db, actor, course_id, review_id)
    ts = service.tasks(db, row)
    if not manager:
        if not subject_key or subject_key not in {t.subject_key for t in assigned}: raise HTTPException(403, 'Download only an assigned subject')
    nodes = service.branch(row.proposed_nodes, subject_key) if subject_key else row.proposed_nodes
    if not nodes: raise HTTPException(409, 'Save syllabus content before downloading')
    if subject_key: ts = [t for t in ts if t.subject_key == subject_key]
    current_keys = {n['key'] for n in nodes if n['level'] == 'subject'}
    ts = [t for t in ts if t.subject_key in current_keys]
    # Review copies show the expert proposal, clearly labelled, without changing live content.
    if subject_key and ts and ts[0].status in {'IN_REVIEW', 'RETURNED', 'RECOMMENDED'}: nodes = ts[0].proposed_nodes or nodes
    version = db.query(models.SyllabusRevision).filter_by(review_id=row.id).first()
    from types import SimpleNamespace
    status_tasks = ts + [SimpleNamespace(status='NOT_REQUESTED') for key in current_keys if key not in {t.subject_key for t in ts}]
    status = service.document_status(row, status_tasks, bool(version and version.published_at))
    from app.services.syllabus_pdf import build_review_pdf
    content = build_review_pdf(course, row, nodes, status, [task_data(db, t) for t in ts], actor.name,
        published_at=version.published_at if version else None)
    return Response(content, media_type='application/pdf', headers={'Cache-Control': 'no-store',
        'Content-Disposition': f'attachment; filename="SYS_Syllabus_Course_{course_id}_Draft_{row.id}_v{row.version}.pdf"'})
