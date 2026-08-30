"""Authorized syllabus drafts, approvals, workbook previews and approved downloads."""
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import update
from app import models, database
from app.routes.auth import get_current_user
from app.syllabus_schemas import StartReview, SaveReview, ReviewAction, WorkbookPreview
from app.services import syllabus_review as service, syllabus_workbook

router = APIRouter(prefix="/courses/{course_id}/syllabus-review", tags=["Syllabus governance"])


def serialize(db, row, *, full=False):
    author = db.get(models.User, row.author_id)
    decider = db.get(models.User, row.decided_by) if row.decided_by else None
    value = {name: getattr(row, name) for name in ("id", "course_id", "subject_id", "author_id", "status", "version",
        "base_revision", "summary", "decision_comment", "created_at", "submitted_at", "decided_at")}
    value.update(author_name=author.name if author else "Former faculty", decided_by_name=decider.name if decider else None)
    if full:
        value.update(nodes=row.proposed_nodes, base_nodes=row.base_nodes, changes=service.changes(row.base_nodes, row.proposed_nodes))
        value["history"] = [dict(action=a.action, at=a.created_at, details=a.details) for a in db.query(models.AdminAuditLog).filter_by(
            target_type="syllabus_review", target_id=row.id).order_by(models.AdminAuditLog.id).all()]
    return value


def load(db, actor, course_id, review_id, *, write=False):
    course, _ = service.course_scope(db, actor, course_id, write=write)
    row = db.query(models.SyllabusReview).filter_by(id=review_id, course_id=course_id).with_for_update().first()
    if not row: raise HTTPException(404, "Review not found")
    if not service.manager(db, actor, course_id) and row.author_id != actor.id:
        raise HTTPException(403, "This review belongs to another faculty member")
    if row.author_id != actor.id and row.status == "DRAFT" and not service.manager(db, actor, course_id):
        raise HTTPException(403, "Unsubmitted drafts are private to their author")
    if row.subject_id and not (service.manager(db, actor, course_id) or service.is_subject_expert(db, actor, row.subject_id)):
        raise HTTPException(403, "Subject assignment has changed")
    return course, row


def claim(db, row, version):
    result = db.execute(update(models.SyllabusReview).where(models.SyllabusReview.id == row.id,
        models.SyllabusReview.version == version).values(version=version+1), execution_options={"synchronize_session": False})
    if result.rowcount != 1: raise HTTPException(409, "Review changed in another window. Reload before editing.")
    db.refresh(row)


def editable(actor, row):
    if row.author_id != actor.id: raise HTTPException(403, "Only the proposal author may edit it")
    if row.status not in {"DRAFT", "CHANGES_REQUESTED"}: raise HTTPException(409, "Withdraw or revise a returned proposal before editing")


def dispatch_later(notification_id):
    from app.services.notifications import dispatch_notification
    with database.SessionLocal() as db:
        dispatch_notification(db, notification_id)


@router.get("")
def workspace(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, subject_ids = service.course_scope(db, actor, course_id)
    if (actor.role or "").lower() == "student": raise HTTPException(403, "Students may download approved syllabuses, not access reviews")
    query = db.query(models.SyllabusReview).filter_by(course_id=course_id)
    if not service.manager(db, actor, course_id): query = query.filter_by(author_id=actor.id)
    revisions = db.query(models.SyllabusRevision).filter_by(course_id=course_id).order_by(models.SyllabusRevision.number.desc()).all()
    return dict(course_id=course_id, course_title=course.title, actor_id=actor.id,
        can_manage=service.manager(db, actor, course_id), archived=course.publication_status == "ARCHIVED",
        revision=course.syllabus_revision, nodes=service.scoped(service.snapshot(db, course_id), subject_ids),
        reviews=[serialize(db, r) for r in query.order_by(models.SyllabusReview.id.desc()).limit(100)],
        revisions=[dict(number=r.number, approved_at=r.created_at, summary=r.summary) for r in revisions])


@router.post("/reviews", status_code=201)
def start(course_id: int, body: StartReview, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, subject_ids = service.course_scope(db, actor, course_id, write=True)
    if not service.manager(db, actor, course_id): raise HTTPException(403, "Wait for an assigned subject review request")
    if body.subject_id: raise HTTPException(422, "Prepare a whole-course working syllabus; request reviews per subject")
    existing = db.query(models.SyllabusReview).filter(models.SyllabusReview.course_id == course_id,
        models.SyllabusReview.subject_id.is_(None), models.SyllabusReview.status.in_(["DRAFT", "CHANGES_REQUESTED"])).first()
    if existing: return serialize(db, existing, full=True)
    if body.subject_id is not None:
        subject = db.get(models.Subject, body.subject_id)
        if not subject or subject.course_id != course_id: raise HTTPException(422, "Subject does not belong to course")
    if subject_ids is not None and body.subject_id not in subject_ids:
        raise HTTPException(403, "Select an assigned subject")
    nodes = service.snapshot(db, course_id)
    baseline = service.scoped(nodes, {body.subject_id}) if body.subject_id else nodes
    row = models.SyllabusReview(course_id=course_id, subject_id=body.subject_id, author_id=actor.id,
        base_revision=course.syllabus_revision, base_hash=service.fingerprint(nodes), base_nodes=baseline,
        proposed_nodes=baseline, summary="", decision_comment="", status="DRAFT", version=1)
    db.add(row); db.flush()
    from app.services.syllabus_subjects import carry_approvals
    carry_approvals(db, row)
    service.audit(db, actor, row, "draft_created"); db.commit()
    return serialize(db, row, full=True)


@router.get("/reviews/{review_id}")
def detail(course_id: int, review_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    _, row = load(db, actor, course_id, review_id)
    return serialize(db, row, full=True)


@router.put("/reviews/{review_id}")
def save(course_id: int, review_id: int, body: SaveReview, background: BackgroundTasks, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    _, row = load(db, actor, course_id, review_id, write=True)
    if not service.manager(db, actor, course_id): raise HTTPException(403, "Use your assigned subject review to propose changes")
    if row.status not in {"DRAFT", "CHANGES_REQUESTED"}: raise HTTPException(409, "Start a new working syllabus before editing")
    desired = service.validate_nodes([n.model_dump() for n in body.nodes], row.base_nodes, faculty=bool(row.subject_id))
    claim(db, row, body.version)
    from app.services.syllabus_subjects import invalidate
    notification_ids = invalidate(db, actor, row, desired)
    row.proposed_nodes, row.summary = desired, body.summary.strip()
    service.audit(db, actor, row, "draft_saved", {"changes": service.changes(row.base_nodes, desired)})
    db.commit()
    for identifier in notification_ids:
        if identifier: background.add_task(dispatch_later, identifier)
    return serialize(db, row, full=True)


@router.post("/reviews/{review_id}/action")
def action(course_id: int, review_id: int, body: ReviewAction, background: BackgroundTasks,
           db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    raise HTTPException(409, "Use Reviews & Approvals to request and decide subject-wise expert reviews")


@router.get("/reviews/{review_id}/workbook.xlsx")
def workbook(course_id: int, review_id: int, blank: bool = False, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, row = load(db, actor, course_id, review_id)
    if not service.manager(db, actor, course_id): raise HTTPException(403, "Workbook upload/download is restricted to administrators and coordinators")
    if row.status not in {"DRAFT", "CHANGES_REQUESTED"}: raise HTTPException(409, "Open a working syllabus to download an editing workbook")
    content = syllabus_workbook.build_workbook(row, course, blank=blank)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="SYS_Syllabus_{"Template" if blank else "Current"}_Course_{course_id}_v{row.version}.xlsx"', "Cache-Control": "no-store"})


@router.post("/reviews/{review_id}/workbook-preview")
def preview(course_id: int, review_id: int, body: WorkbookPreview, db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    _, row = load(db, actor, course_id, review_id, write=True)
    if not service.manager(db, actor, course_id): raise HTTPException(403, "Subject experts use the syllabus review page, not workbook upload")
    if row.status not in {"DRAFT", "CHANGES_REQUESTED"}: raise HTTPException(409, "Open a working syllabus before uploading")
    if body.version != row.version: raise HTTPException(409, "Draft changed; download the latest workbook")
    nodes = syllabus_workbook.parse(row, body)
    return {"nodes": nodes, "changes": service.changes(row.proposed_nodes, nodes), "item_count": len(nodes)}


@router.get("/approved.pdf")
def approved_pdf(course_id: int, revision: int | None = Query(None, ge=1), subject_id: int | None = Query(None, ge=1),
                 db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    course, allowed = service.course_scope(db, actor, course_id)
    if revision is None and service.manager(db, actor, course_id):
        draft = db.query(models.SyllabusReview).filter(models.SyllabusReview.course_id == course_id,
            models.SyllabusReview.subject_id.is_(None), models.SyllabusReview.status.in_(['DRAFT', 'CHANGES_REQUESTED'])).order_by(models.SyllabusReview.id.desc()).first()
        if draft and draft.proposed_nodes:
            from app.routes.syllabus_subjects import pdf
            return pdf(course_id, draft.id, f'subject:{subject_id}' if subject_id else None, db, actor)
    if subject_id is not None:
        subject = db.get(models.Subject, subject_id)
        if not subject or subject.course_id != course_id: raise HTTPException(404, "Subject not found")
        if allowed is not None and subject_id not in allowed: raise HTTPException(403, "Subject is outside your responsibility")
        allowed = {subject_id}
    version = db.query(models.SyllabusRevision).filter_by(course_id=course_id, number=revision or course.syllabus_revision).first()
    if not version: raise HTTPException(409, "No approved syllabus version exists yet. Complete coordinator approval first.")
    if (actor.role or '').lower() == 'student' and not version.published_at:
        raise HTTPException(403, 'Students may download only published syllabus versions')
    from app.services.syllabus_pdf import build_approved_pdf
    approver = db.get(models.User, version.approved_by)
    from app.routes.syllabus_subjects import task_data
    subject_facts = []
    for task in db.query(models.SyllabusSubjectReview).filter_by(review_id=version.review_id):
        if task.live_subject_id and (allowed is None or task.live_subject_id in allowed):
            subject_facts.append({**task_data(db, task), 'subject_key': f'subject:{task.live_subject_id}'})
    content = build_approved_pdf(version, service.scoped(version.nodes, allowed), approver.name if approver else "Authorized coordinator", subject_facts)
    return Response(content, media_type="application/pdf", headers={"Cache-Control": "no-store",
        "Content-Disposition": f'attachment; filename="SYS_Approved_Syllabus_{course_id}_v{version.number}.pdf"'})
