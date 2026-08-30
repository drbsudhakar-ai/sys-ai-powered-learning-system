"""Manager-only view of saved syllabus configuration, never a learning snapshot.

Draft keys remain stable until approval. Both administrative screens consume this
view, so initial upload/reset need no destructive copies into live academic tables.
"""
from app import models
from app.services import syllabus_review as core


def assignable(user):
    return bool(user and (user.role or '').lower() == 'faculty' and user.is_active
                and (user.employment_status or 'ACTIVE').upper() != 'INACTIVE'
                and user.account_status in {'ACTIVE', 'PENDING_ACTIVATION'})


def configuration(db, course):
    review = db.query(models.SyllabusReview).filter(
        models.SyllabusReview.course_id == course.id,
        models.SyllabusReview.subject_id.is_(None),
        models.SyllabusReview.status.in_(['DRAFT', 'CHANGES_REQUESTED'])
    ).order_by(models.SyllabusReview.id.desc()).first()
    nodes = review.proposed_nodes if review else core.snapshot(db, course.id)
    tasks = {t.subject_key: t for t in db.query(models.SyllabusSubjectReview).filter_by(review_id=review.id)} if review else {}
    subjects, experts = [], []
    approved = 0
    for node in nodes:
        if node['level'] != 'subject':
            continue
        key = node['key']
        live_id = int(key.split(':')[1]) if key.startswith('subject:') else None
        identifier = live_id or f'draft:{review.id}:{key}'
        subject = dict(id=identifier, name=node['name'], course_id=course.id,
                       course_title=course.title, subject_key=key,
                       draft_review_id=review.id if review else None,
                       draft_version=review.version if review else None)
        subjects.append(subject)
        task = tasks.get(key)
        assigned = db.query(models.SubjectExpertAssignment).filter_by(subject_id=live_id).all() if live_id else []
        people = {a.faculty_id: a.id for a in assigned}
        if task and task.reviewer_id and not live_id:
            people[task.reviewer_id] = f'draft:{task.id}'
        for person_id, assignment_id in people.items():
            person = db.get(models.User, person_id)
            if not person:
                continue
            experts.append(dict(id=assignment_id, faculty_id=person.id, faculty_name=person.name,
                faculty_email=person.email, subject_id=identifier, subject_name=node['name'],
                course_id=course.id, course_title=course.title, subject_key=key,
                draft_review_id=review.id if review and not live_id else None,
                draft_version=review.version if review else None,
                assignment_valid=assignable(person),
                can_remove=not task or task.status in {'NOT_REQUESTED', 'CANCELLED'},
                account_status=person.account_status))
        if task and task.status == 'APPROVED':
            from app.services.syllabus_subjects import valid_reviewer, branch
            if valid_reviewer(db, task) and task.source_hash == core.fingerprint(branch(nodes, key)):
                approved += 1
    if not review and course.syllabus_revision:
        approved = len(subjects)
    return dict(subjects=subjects, experts=experts,
                review_id=review.id if review else None, version=review.version if review else None,
                status='WORKING_DRAFT' if review else 'APPROVED' if course.syllabus_revision else 'CONFIGURED',
                approved_subject_count=approved,
                **{f'{level}_count': sum(n['level'] == level for n in nodes)
                   for level in ('subject', 'unit', 'topic', 'subtopic')})
