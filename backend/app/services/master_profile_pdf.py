"""Branded, administrator-authorized SYS student and faculty profile reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SYS_BLUE = colors.HexColor("#082A66")
SYS_PURPLE = colors.HexColor("#6333A0")
SYS_INK = colors.HexColor("#20304E")
SYS_MUTED = colors.HexColor("#66758C")
SYS_PALE = colors.HexColor("#F2F6FF")
SYS_BORDER = colors.HexColor("#DFE6F1")
IST = timezone(timedelta(hours=5, minutes=30))


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError("Profile data must be a mapping or a Pydantic model")


def _display(value: Any, default: str = "Not available") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return f"{value.astimezone(IST).strftime('%d %b %Y, %I:%M %p')} IST"
    return str(value)


def _status(value: Any) -> str:
    text = _display(value)
    if text.startswith("PENDING"):
        return "Pending registration"
    return text.replace("_", " ").title()


def _initials(name: str) -> str:
    words = [word for word in name.replace(".", " ").split() if word.lower() not in {"dr", "mr", "mrs", "ms", "prof"}]
    if not words:
        return "SY"
    if len(words) == 1:
        return words[0][:2].upper()
    return f"{words[0][0]}{words[-1][0]}".upper()


def _local_photo(photo_url: str | None) -> Path | None:
    if not photo_url:
        return None
    parsed = urlparse(str(photo_url))
    if parsed.scheme or parsed.netloc:
        return None
    public_root = Path(__file__).resolve().parents[3] / "frontend" / "public"
    candidate = (public_root / unquote(parsed.path).lstrip("/")).resolve()
    if not candidate.is_relative_to(public_root.resolve()):
        return None
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or not candidate.is_file():
        return None
    return candidate


def _default_profile_photo_url(record: dict, kind: str) -> str | None:
    if kind not in {"student", "faculty"}:
        return None
    identifier = record.get("roll_number") if kind == "student" else record.get("employee_code")
    if not identifier or not re.fullmatch(r"[A-Za-z0-9_-]+", str(identifier)):
        return None
    return f"/photos/{kind}-{identifier}.jpg"


def _logo_path() -> Path | None:
    logo = Path(__file__).resolve().parents[3] / "frontend" / "public" / "branding" / "sys-v2" / "logos" / "SYS_Symbol_Compact_Transparent.png"
    fallback = Path(__file__).resolve().parents[1] / "assets" / "SYS_Symbol_Master_Transparent.png"
    for candidate in (logo, fallback):
        if candidate.is_file():
            try:
                ImageReader(str(candidate)).getRGBData()
                return candidate
            except Exception:
                continue
    return None


class _InitialsAvatar(Flowable):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.width = 24 * mm
        self.height = 24 * mm

    def draw(self):
        self.canv.setFillColor(SYS_PALE)
        self.canv.roundRect(0, 0, self.width, self.height, 7 * mm, fill=1, stroke=0)
        self.canv.setFillColor(SYS_BLUE)
        self.canv.setFont("Helvetica-Bold", 20)
        self.canv.drawCentredString(self.width / 2, self.height / 2 - 7, _initials(self.name))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("SYSProfileName", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=SYS_BLUE, spaceAfter=5),
        "subtitle": ParagraphStyle("SYSProfileSubtitle", parent=base["Normal"], fontSize=9, leading=13, textColor=SYS_MUTED),
        "section": ParagraphStyle("SYSProfileSection", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=SYS_BLUE, spaceBefore=3, spaceAfter=9),
        "label": ParagraphStyle("SYSProfileLabel", parent=base["Normal"], fontSize=8, leading=11, textColor=SYS_MUTED),
        "value": ParagraphStyle("SYSProfileValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.6, leading=12, textColor=SYS_INK, wordWrap="CJK"),
        "notice": ParagraphStyle("SYSProfileNotice", parent=base["Normal"], fontSize=8, leading=12, textColor=SYS_MUTED),
        "empty": ParagraphStyle("SYSProfileEmpty", parent=base["Normal"], fontSize=8.5, leading=13, textColor=SYS_MUTED),
    }


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_display(value)), style)


def _section(title: str, pairs: list[tuple[str, Any]], styles: dict[str, ParagraphStyle], width: float) -> list:
    rows = []
    for index in range(0, len(pairs), 2):
        cells = []
        for label, value in pairs[index:index + 2]:
            cells.append([
                _paragraph(label, styles["label"]),
                Spacer(1, 2),
                _paragraph(value, styles["value"]),
            ])
        if len(cells) == 1:
            cells.append("")
        rows.append(cells)
    table = Table(rows, colWidths=[width / 2, width / 2], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.65, SYS_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, SYS_BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAFBFE")]),
    ]))
    return [KeepTogether([Paragraph(escape(title), styles["section"]), table]), Spacer(1, 13)]


def _header_footer(canvas, doc, *, title: str, generated_at: datetime, generated_by: str):
    page_width, page_height = A4
    canvas.saveState()
    canvas.setFillColor(SYS_BLUE)
    canvas.rect(0, page_height - 76, page_width, 76, fill=1, stroke=0)
    canvas.setFillColor(SYS_PURPLE)
    canvas.rect(0, page_height - 81, page_width, 5, fill=1, stroke=0)
    logo = _logo_path()
    text_x = 22 * mm
    if logo:
        try:
            logo_x = 16 * mm
            logo_size = 42
            logo_y = page_height - 60
            canvas.setFillColor(colors.white)
            canvas.roundRect(logo_x, logo_y, logo_size, logo_size, 8, fill=1, stroke=0)
            canvas.drawImage(ImageReader(str(logo)), logo_x + 5, logo_y + 5, width=32, height=32, preserveAspectRatio=True, mask="auto")
            text_x = logo_x + logo_size + 13
        except Exception:
            text_x = 22 * mm
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(text_x, page_height - 31, "SYS - Strengthen Your Skills")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(text_x, page_height - 46, "Shape Your Successful Future")
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawRightString(page_width - 18 * mm, page_height - 33, title.upper())

    canvas.setStrokeColor(SYS_BORDER)
    canvas.line(18 * mm, 18 * mm, page_width - 18 * mm, 18 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SYS_MUTED)
    canvas.drawString(18 * mm, 13 * mm, "Confidential - For authorized institutional use only")
    canvas.drawRightString(page_width - 18 * mm, 13 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_master_profile_pdf(profile: Any, *, generated_by: str, generated_at: datetime | None = None) -> bytes:
    """Build a branded institutional profile without fetching untrusted photo URLs."""

    payload = _as_dict(profile)
    record = _as_dict(payload["record"])
    activity = payload.get("activity") or {}
    kind = str(record.get("role", "student")).lower()
    issued_at = (generated_at or datetime.now(IST)).astimezone(IST)
    title = f"{kind.title()} Master Profile"
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=95, bottomMargin=68, pageCompression=0, title=f"SYS {title}", author="SYS - Strengthen Your Skills")
    styles = _styles()
    available_width = A4[0] - 36 * mm
    name = _display(record.get("name"), "SYS profile")
    identifier_label = "Roll number" if kind == "student" else "Employee code"
    identifier = _display(record.get("roll_number") if kind == "student" else record.get("employee_code"))
    photo_path = _local_photo(record.get("photo_url") or _default_profile_photo_url(record, kind))
    avatar = Image(str(photo_path), width=24 * mm, height=24 * mm, kind="proportional") if photo_path else _InitialsAvatar(name)
    identity = Table([[
        avatar,
        [
            _paragraph(name, styles["name"]),
            _paragraph(f"{identifier_label}: {identifier}", styles["subtitle"]),
            _paragraph(f"Registration: {_status(record.get('registration_status'))}", styles["subtitle"]),
        ],
    ]], colWidths=[29 * mm, available_width - 29 * mm])
    identity.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 11)]))
    story = [identity, _paragraph(f"Generated: {issued_at.strftime('%d %b %Y, %I:%M:%S %p')} IST   |   Generated by: {generated_by}", styles["notice"]), Spacer(1, 16)]

    contact = [
        ("Email address", _display(record.get("email"))),
        ("Mobile number", _display(record.get("mobile_number"))),
        ("Email verification", "Verified" if record.get("email_verified") else "Not verified"),
        ("Mobile verification", "Verified" if record.get("mobile_verified") else "Not verified"),
    ]
    story.extend(_section("Contact information", contact, styles, available_width))

    if kind == "student":
        academic = [
            ("College", _display(record.get("college"))),
            ("Academic programme", _display(record.get("academic_program"))),
            ("Admission year", _display(record.get("admission_year"))),
            ("Present year", _display(record.get("present_year"))),
            ("Academic status", _status(record.get("academic_status"))),
            ("Institutional identifier", identifier),
        ]
        story.extend(_section("Academic information", academic, styles, available_width))
        programmes = record.get("programmes") or []
        programme_pairs = [(f"Programme {index}", _as_dict(item).get("title", "Not available")) for index, item in enumerate(programmes, start=1)]
        story.extend(_section("Registered SYS courses", programme_pairs or [("Enrollment status", "No SYS courses enrolled")], styles, available_width))

        learning = activity.get("learning") or {}
        story.extend(_section("Learning sessions and progress", [
            ("Learning status", "Learning in progress" if learning.get("total") else "Learning has not started yet"),
            ("Sessions attended", learning.get("total", 0)),
            ("Completed sessions", learning.get("completed", 0)),
            ("Currently in progress", learning.get("in_progress", 0)),
        ], styles, available_width))

        assessments = activity.get("assessments") or {}
        average = assessments.get("average_percentage")
        best = assessments.get("best_percentage")
        story.extend(_section("Assessment performance", [
            ("Assessment status", "Assessments attempted" if assessments.get("attempted") else "No assessments attempted yet"),
            ("Assessments attempted", assessments.get("attempted", 0)),
            ("Completed assessments", assessments.get("completed", 0)),
            ("Average score", f"{average}%" if average is not None else "Not assessed yet"),
            ("Best score", f"{best}%" if best is not None else "Not assessed yet"),
        ], styles, available_width))

        performance = activity.get("performance") or {}
        story.extend(_section("Performance analysis and learning gaps", [
            ("Analysis status", "Performance analyzed" if performance.get("analyses") else "Performance analysis has not started yet"),
            ("Performance analyses", performance.get("analyses", 0)),
            ("Identified learning gaps", performance.get("learning_gaps", 0)),
            ("High-priority gaps", performance.get("high_priority_gaps", 0)),
            ("Performance trend", _display(performance.get("trend"), "Not available yet")),
        ], styles, available_width))

        remediation = activity.get("remediation") or {}
        story.extend(_section("Remedial learning and interventions", [
            ("Remedial status", "Remedial support assigned" if remediation.get("interventions") else "No remedial support assigned yet"),
            ("Remedial groups", remediation.get("groups", 0)),
            ("Interventions assigned", remediation.get("interventions", 0)),
            ("Active interventions", remediation.get("active", 0)),
            ("Completed interventions", remediation.get("completed", 0)),
            ("Pending reassessments", remediation.get("reassessments_pending", 0)),
        ], styles, available_width))

        mastery = activity.get("mastery") or {}
        mastery_average = mastery.get("average_mastery")
        story.extend(_section("Topic mastery and adaptive practice", [
            ("Mastery status", "Mastery tracking active" if mastery.get("topics") else "Mastery tracking has not started yet"),
            ("Topics tracked", mastery.get("topics", 0)),
            ("Topics mastered", mastery.get("mastered", 0)),
            ("Average mastery", f"{mastery_average}%" if mastery_average is not None else "Not assessed yet"),
            ("Practice assignments", mastery.get("practice_assigned", 0)),
            ("Practice completed", mastery.get("practice_completed", 0)),
        ], styles, available_width))

        journey = activity.get("journey") or {}
        story.extend(_section("Learning journey and next action", [
            ("Journey status", "Learning journey active" if journey.get("total_actions") else "Learning journey has not started yet"),
            ("Recommended actions", journey.get("total_actions", 0)),
            ("Pending actions", journey.get("pending_actions", 0)),
            ("Completed actions", journey.get("completed_actions", 0)),
            ("Next recommended action", _display(journey.get("next_action"), "No action recommended yet")),
        ], styles, available_width))

        support = activity.get("support") or {}
        story.extend(_section("Early warnings and student support", [
            ("Support status", "Attention required" if support.get("high_priority_gaps") or support.get("pending_remediation") else "No academic warnings identified yet"),
            ("High-priority learning gaps", support.get("high_priority_gaps", 0)),
            ("Active remedial support", support.get("pending_remediation", 0)),
            ("Pending learning actions", support.get("pending_journey_actions", 0)),
        ], styles, available_width))

        communication = [item for item in programmes if re.search(r"english|communication|spoken", _as_dict(item).get("title", ""), flags=re.IGNORECASE)]
        story.extend(_section("English communication and skill development", [
            ("Enrollment status", "Enrolled" if communication else "Not registered for an English communication programme yet"),
            ("Communication programmes", len(communication)),
        ], styles, available_width))
    else:
        professional = [
            ("College", _display(record.get("college"))),
            ("Department", _display(record.get("department"))),
            ("Designation", _display(record.get("designation"))),
            ("Employment status", _status(record.get("employment_status"))),
        ]
        story.extend(_section("Professional information", professional, styles, available_width))
        courses = payload.get("coordinator_courses") or []
        subjects = payload.get("expert_subjects") or []
        responsibility_pairs = [
            ("Coordinator courses", ", ".join(_as_dict(item).get("title", "") for item in courses) or "None assigned"),
            ("Subject expertise", ", ".join(_as_dict(item).get("name", "") for item in subjects) or "None assigned"),
            ("Coordinator assignments", len(courses)),
            ("Subject expert assignments", len(subjects)),
        ]
        story.extend(_section("Academic responsibilities", responsibility_pairs, styles, available_width))

        teaching = activity.get("teaching") or {}
        story.extend(_section("Teaching and learning sessions", [
            ("Teaching status", "Teaching activity recorded" if teaching.get("total") else "No teaching sessions have started yet"),
            ("Sessions facilitated", teaching.get("total", 0)),
            ("Completed sessions", teaching.get("completed", 0)),
            ("Currently in progress", teaching.get("in_progress", 0)),
        ], styles, available_width))

        assessments = activity.get("assessments") or {}
        story.extend(_section("Assessment creation and evaluation", [
            ("Assessment status", "Assessments created" if assessments.get("created") else "No assessments created yet"),
            ("Assessments created", assessments.get("created", 0)),
            ("Published assessments", assessments.get("published", 0)),
            ("Draft assessments", assessments.get("draft", 0)),
            ("Student attempts", assessments.get("student_attempts", 0)),
        ], styles, available_width))

        oversight = activity.get("oversight") or {}
        story.extend(_section("Student performance and academic oversight", [
            ("Oversight status", "Course coordination assigned" if oversight.get("coordinator_courses") else "No student oversight assigned yet"),
            ("Coordinated courses", oversight.get("coordinator_courses", 0)),
            ("Students under coordination", oversight.get("students", 0)),
            ("Identified learning gaps", oversight.get("learning_gaps", 0)),
            ("High-priority gaps", oversight.get("high_priority_gaps", 0)),
        ], styles, available_width))

        remediation = activity.get("remediation") or {}
        story.extend(_section("Remedial guidance and interventions", [
            ("Guidance status", "Remedial activity recorded" if remediation.get("interventions_created") else "No remedial interventions created yet"),
            ("Remedial groups created", remediation.get("groups_created", 0)),
            ("Interventions created", remediation.get("interventions_created", 0)),
            ("Active interventions", remediation.get("active", 0)),
            ("Completed interventions", remediation.get("completed", 0)),
        ], styles, available_width))

        content = activity.get("content") or {}
        story.extend(_section("Question bank and academic content", [
            ("Content status", "Academic content created" if content.get("questions_created") or content.get("courses_created") else "No academic content created yet"),
            ("Questions created", content.get("questions_created", 0)),
            ("SYS courses created", content.get("courses_created", 0)),
        ], styles, available_width))

    notifications = activity.get("notifications") or {}
    story.extend(_section("Notifications and engagement", [
        ("Communication status", "Notifications received" if notifications.get("total") else "No notifications recorded yet"),
        ("Notifications received", notifications.get("total", 0)),
        ("Unread notifications", notifications.get("unread", 0)),
    ], styles, available_width))

    account = [
        ("Registration status", _status(record.get("registration_status"))),
        ("Account status", "Enabled" if record.get("is_active") else "Inactive"),
        ("Created", _display(record.get("created_at"))),
        ("Last updated", _display(record.get("updated_at"))),
        ("Last login", _display(record.get("last_login_at"), "No login recorded") if record.get("last_login_available") else "No login recorded"),
    ]
    story.extend(_section("Account and record activity", account, styles, available_width))
    page_callback = lambda canvas, doc: _header_footer(canvas, doc, title=title, generated_at=issued_at, generated_by=generated_by)
    document.build(story, onFirstPage=page_callback, onLaterPages=page_callback)
    return output.getvalue()
