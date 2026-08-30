"""SYS-branded approved syllabus; no personal student/faculty contact data."""
from datetime import datetime, timezone
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer
from app.services.master_profile_pdf import IST, SYS_BLUE, SYS_PURPLE, _header_footer, _paragraph, _styles

def timestamp(value):
    if not value: return 'Not recorded'
    if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST).strftime('%d %b %Y, %I:%M %p IST')

def build_review_pdf(course, review, nodes, status, subjects, downloaded_by, published_at=None):
    """Saved-version print copy: status repeated on every page, never inferred from a filename."""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    output = BytesIO(); issued = datetime.now(IST); styles = _styles()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=112, bottomMargin=76, title='SYS Syllabus - ' + status, author='SYS - Strengthen Your Skills')
    story = [_paragraph(course.title, styles['name']), _paragraph(status, styles['section']),
        _paragraph(f'Course: {course.programme_code or "Not configured"} | Saved syllabus {review.id}, version {review.version}', styles['subtitle']),
        _paragraph('Generated: ' + timestamp(issued), styles['notice']),
        _paragraph('Academic approval is institutional approval, not examination-authority endorsement.', styles['notice'])]
    if published_at: story.append(_paragraph('This exact version published: ' + timestamp(published_at), styles['notice']))
    subject_nodes = [n for n in nodes if n['level'] == 'subject']
    for node in subject_nodes:
        task = next((t for t in subjects if t['subject_key'] == node['key']), {})
        rows = [[_paragraph(node['name'], styles['value']), _paragraph(task.get('status', 'NOT_REQUESTED').replace('_', ' '), styles['notice'])],
            [_paragraph('Subject expert: ' + (task.get('reviewer_name') or 'Not assigned'), styles['notice']), _paragraph('Recommendation: ' + timestamp(task.get('recommended_at')), styles['notice'])],
            [_paragraph('Final approver: ' + (task.get('approver_name') or 'Pending'), styles['notice']), _paragraph('Final approval: ' + timestamp(task.get('approved_at')), styles['notice'])]]
        table = Table(rows, colWidths=[88*mm, 86*mm]); table.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('BOX',(0,0),(-1,-1),.5,SYS_PURPLE),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eff3fc')), ('TOPPADDING',(0,0),(-1,-1),7), ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([Spacer(1,10),table])
    groups = {}
    for n in nodes: groups.setdefault(n['parent'], []).append(n)
    def render(parent, depth=0, prefix=''):
        for index, n in enumerate(sorted(groups.get(parent, []), key=lambda x:(x['sequence'],x['name'])),1):
            number = f'{prefix}{index}.'
            heading = ParagraphStyle('h'+str(depth), parent=styles['value'], leftIndent=depth*10,
                textColor=SYS_BLUE if depth % 2 == 0 else SYS_PURPLE, spaceBefore=12, keepWithNext=True)
            detail = ParagraphStyle('d'+str(depth), parent=styles['notice'], leftIndent=depth*10, spaceAfter=5)
            story.append(_paragraph(f'{number} {n["name"]}', heading))
            story.append(_paragraph(n.get('description') or 'No description recorded.', detail))
            if n.get('learning_outcome'): story.append(_paragraph('Learning outcome: '+n['learning_outcome'], detail))
            render(n['key'],depth+1,number)
    render(None)
    if status not in {'APPROVED AND PUBLISHED', 'APPROVED - NOT YET PUBLISHED'}:
        story.extend([Spacer(1,18),_paragraph('Handwritten review notes (enter recommendations into SYS after verification)',styles['section'])])
        for _ in range(4): story.append(_paragraph('_' * 90, styles['notice'])); story.append(Spacer(1,12))
    def page(canvas, document):
        _header_footer(canvas, document, title='', generated_at=issued, generated_by=downloaded_by)
        canvas.saveState(); canvas.setFillColor(SYS_PURPLE); canvas.setFont('Helvetica-Bold',8)
        canvas.drawString(18*mm,A4[1]-99,status)
        if 'NOT APPROVED' in status or 'REVIEW' in status:
            canvas.setFillColor(colors.HexColor('#eeeeF4')); canvas.setFont('Helvetica-Bold',45)
            canvas.translate(A4[0]/2,A4[1]/2); canvas.rotate(35); canvas.drawCentredString(0,0,'REVIEW COPY')
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return output.getvalue()


def build_approved_pdf(version, nodes, approver, subjects=None):
    from types import SimpleNamespace
    course = SimpleNamespace(title=version.course_title, programme_code=version.programme_code)
    review = SimpleNamespace(id=version.review_id, version=version.number)
    status = 'APPROVED AND PUBLISHED' if getattr(version, 'published_at', None) else 'APPROVED - NOT YET PUBLISHED'
    subjects = subjects or [dict(subject_key=n['key'], status='APPROVED', approver_name=approver, approved_at=version.created_at) for n in nodes if n['level']=='subject']
    return build_review_pdf(course, review, nodes, status, subjects, approver, getattr(version,'published_at',None))
