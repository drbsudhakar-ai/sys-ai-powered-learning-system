"""Dependency-free, safely formatted Excel workbooks for SYS master exports."""

from __future__ import annotations

from datetime import datetime, timezone
import io
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("", SHEET_NS)
ET.register_namespace("r", REL_NS)
ET.register_namespace("cp", CORE_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)


def _column_name(index: int) -> str:
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _xml(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _content_types() -> bytes:
    root = ET.Element(f"{{{CONTENT_NS}}}Types")
    for extension, content_type in (
        ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
        ("xml", "application/xml"),
    ):
        ET.SubElement(root, f"{{{CONTENT_NS}}}Default", Extension=extension, ContentType=content_type)
    overrides = {
        "/xl/workbook.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        "/xl/worksheets/sheet1.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        "/xl/styles.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
        "/docProps/core.xml": "application/vnd.openxmlformats-package.core-properties+xml",
        "/docProps/app.xml": "application/vnd.openxmlformats-officedocument.extended-properties+xml",
    }
    for name, content_type in overrides.items():
        ET.SubElement(root, f"{{{CONTENT_NS}}}Override", PartName=name, ContentType=content_type)
    return _xml(root)


def _relationships(items: Iterable[tuple[str, str, str]]) -> bytes:
    root = ET.Element(f"{{{PACKAGE_REL_NS}}}Relationships")
    for identifier, relationship, target in items:
        ET.SubElement(root, f"{{{PACKAGE_REL_NS}}}Relationship", Id=identifier, Type=relationship, Target=target)
    return _xml(root)


def _workbook(sheet_name: str) -> bytes:
    root = ET.Element(f"{{{SHEET_NS}}}workbook")
    sheets = ET.SubElement(root, f"{{{SHEET_NS}}}sheets")
    ET.SubElement(sheets, f"{{{SHEET_NS}}}sheet", {
        "name": sheet_name,
        "sheetId": "1",
        f"{{{REL_NS}}}id": "rId1",
    })
    return _xml(root)


def _styles() -> bytes:
    root = ET.Element(f"{{{SHEET_NS}}}styleSheet")

    fonts = ET.SubElement(root, f"{{{SHEET_NS}}}fonts", count="6")
    regular = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(regular, f"{{{SHEET_NS}}}sz", val="11")
    ET.SubElement(regular, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(regular, f"{{{SHEET_NS}}}color", rgb="FF20304E")
    heading = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(heading, f"{{{SHEET_NS}}}b")
    ET.SubElement(heading, f"{{{SHEET_NS}}}sz", val="11")
    ET.SubElement(heading, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(heading, f"{{{SHEET_NS}}}color", rgb="FFFFFFFF")

    brand = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(brand, f"{{{SHEET_NS}}}b")
    ET.SubElement(brand, f"{{{SHEET_NS}}}sz", val="19")
    ET.SubElement(brand, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(brand, f"{{{SHEET_NS}}}color", rgb="FFFFFFFF")
    tagline = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(tagline, f"{{{SHEET_NS}}}i")
    ET.SubElement(tagline, f"{{{SHEET_NS}}}sz", val="11")
    ET.SubElement(tagline, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(tagline, f"{{{SHEET_NS}}}color", rgb="FFFFFFFF")
    title = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(title, f"{{{SHEET_NS}}}b")
    ET.SubElement(title, f"{{{SHEET_NS}}}sz", val="15")
    ET.SubElement(title, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(title, f"{{{SHEET_NS}}}color", rgb="FF082A66")
    note = ET.SubElement(fonts, f"{{{SHEET_NS}}}font")
    ET.SubElement(note, f"{{{SHEET_NS}}}i")
    ET.SubElement(note, f"{{{SHEET_NS}}}sz", val="10")
    ET.SubElement(note, f"{{{SHEET_NS}}}name", val="Aptos")
    ET.SubElement(note, f"{{{SHEET_NS}}}color", rgb="FF52627B")

    fills = ET.SubElement(root, f"{{{SHEET_NS}}}fills", count="5")
    for pattern in ("none", "gray125"):
        fill = ET.SubElement(fills, f"{{{SHEET_NS}}}fill")
        ET.SubElement(fill, f"{{{SHEET_NS}}}patternFill", patternType=pattern)
    for color in ("FF082A66", "FFF2F6FF", "FF6333A0"):
        fill = ET.SubElement(fills, f"{{{SHEET_NS}}}fill")
        pattern = ET.SubElement(fill, f"{{{SHEET_NS}}}patternFill", patternType="solid")
        ET.SubElement(pattern, f"{{{SHEET_NS}}}fgColor", rgb=color)
        ET.SubElement(pattern, f"{{{SHEET_NS}}}bgColor", indexed="64")

    borders = ET.SubElement(root, f"{{{SHEET_NS}}}borders", count="2")
    empty = ET.SubElement(borders, f"{{{SHEET_NS}}}border")
    for edge in ("left", "right", "top", "bottom", "diagonal"):
        ET.SubElement(empty, f"{{{SHEET_NS}}}{edge}")
    lined = ET.SubElement(borders, f"{{{SHEET_NS}}}border")
    for edge in ("left", "right", "top"):
        ET.SubElement(lined, f"{{{SHEET_NS}}}{edge}")
    bottom = ET.SubElement(lined, f"{{{SHEET_NS}}}bottom", style="thin")
    ET.SubElement(bottom, f"{{{SHEET_NS}}}color", rgb="FFE1E7F0")
    ET.SubElement(lined, f"{{{SHEET_NS}}}diagonal")

    cell_style_xfs = ET.SubElement(root, f"{{{SHEET_NS}}}cellStyleXfs", count="1")
    ET.SubElement(cell_style_xfs, f"{{{SHEET_NS}}}xf", numFmtId="0", fontId="0", fillId="0", borderId="0")
    cell_xfs = ET.SubElement(root, f"{{{SHEET_NS}}}cellXfs", count="11")
    configurations = (
        {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"},
        {"numFmtId": "0", "fontId": "1", "fillId": "2", "borderId": "0", "applyFont": "1", "applyFill": "1"},
        {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "1", "applyBorder": "1"},
        {"numFmtId": "0", "fontId": "0", "fillId": "3", "borderId": "1", "applyFill": "1", "applyBorder": "1"},
        {"numFmtId": "49", "fontId": "0", "fillId": "0", "borderId": "1", "applyNumberFormat": "1", "applyBorder": "1"},
        {"numFmtId": "49", "fontId": "0", "fillId": "3", "borderId": "1", "applyNumberFormat": "1", "applyFill": "1", "applyBorder": "1"},
        {"numFmtId": "0", "fontId": "2", "fillId": "2", "borderId": "0", "applyFont": "1", "applyFill": "1"},
        {"numFmtId": "0", "fontId": "3", "fillId": "4", "borderId": "0", "applyFont": "1", "applyFill": "1"},
        {"numFmtId": "0", "fontId": "4", "fillId": "0", "borderId": "0", "applyFont": "1"},
        {"numFmtId": "0", "fontId": "0", "fillId": "3", "borderId": "0", "applyFill": "1"},
        {"numFmtId": "0", "fontId": "5", "fillId": "0", "borderId": "0", "applyFont": "1"},
    )
    for configuration in configurations:
        xf = ET.SubElement(cell_xfs, f"{{{SHEET_NS}}}xf", xfId="0", **configuration)
        ET.SubElement(xf, f"{{{SHEET_NS}}}alignment", vertical="center")
    styles = ET.SubElement(root, f"{{{SHEET_NS}}}cellStyles", count="1")
    ET.SubElement(styles, f"{{{SHEET_NS}}}cellStyle", name="Normal", xfId="0", builtinId="0")
    return _xml(root)


def _worksheet(
    headers: list[str],
    rows: list[list[object]],
    text_columns: set[int],
    report: dict[str, str] | None = None,
) -> bytes:
    root = ET.Element(f"{{{SHEET_NS}}}worksheet")
    final_column = _column_name(len(headers))
    heading_row = 8 if report else 1
    data_final_row = heading_row + len(rows)
    final_row = data_final_row + 2 if report else data_final_row
    ET.SubElement(root, f"{{{SHEET_NS}}}dimension", ref=f"A1:{final_column}{final_row}")
    views = ET.SubElement(root, f"{{{SHEET_NS}}}sheetViews")
    view = ET.SubElement(views, f"{{{SHEET_NS}}}sheetView", workbookViewId="0", showGridLines="0")
    ET.SubElement(view, f"{{{SHEET_NS}}}pane", ySplit=str(heading_row), topLeftCell=f"A{heading_row + 1}", activePane="bottomLeft", state="frozen")
    ET.SubElement(root, f"{{{SHEET_NS}}}sheetFormatPr", defaultRowHeight="18")

    columns = ET.SubElement(root, f"{{{SHEET_NS}}}cols")
    for index, header in enumerate(headers, start=1):
        longest_value = max((len(str(row[index - 1] or "")) for row in rows), default=0)
        width = min(max(len(header) + 4, longest_value + 3, 14), 42)
        if index - 1 in text_columns:
            width = max(width, 19)
        ET.SubElement(columns, f"{{{SHEET_NS}}}col", min=str(index), max=str(index), width=str(width), customWidth="1")

    sheet_data = ET.SubElement(root, f"{{{SHEET_NS}}}sheetData")

    if report:
        report_lines = (
            (1, "SYS — Strengthen Your Skills", "6", "34"),
            (2, "Shape Your Successful Future", "7", "24"),
            (3, report["title"], "8", "29"),
            (4, f"Generated: {report['generated_at']}    |    Generated by: {report['generated_by']}", "9", "23"),
            (5, report["summary"], "9", "23"),
            (6, f"Applied filters: {report['filters']}", "9", "23"),
        )
        for number, value, style, height in report_lines:
            report_row = ET.SubElement(sheet_data, f"{{{SHEET_NS}}}row", r=str(number), ht=height, customHeight="1")
            for column in range(1, len(headers) + 1):
                cell = ET.SubElement(report_row, f"{{{SHEET_NS}}}c", r=f"{_column_name(column)}{number}", s=style, t="inlineStr")
                inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
                ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = value if column == 1 else ""

    heading = ET.SubElement(sheet_data, f"{{{SHEET_NS}}}row", r=str(heading_row), ht="25", customHeight="1")
    for index, value in enumerate(headers, start=1):
        cell = ET.SubElement(heading, f"{{{SHEET_NS}}}c", r=f"{_column_name(index)}{heading_row}", t="inlineStr", s="1")
        inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
        ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = value

    for row_number, values in enumerate(rows, start=heading_row + 1):
        row = ET.SubElement(sheet_data, f"{{{SHEET_NS}}}row", r=str(row_number), ht="20", customHeight="1")
        alternate = row_number % 2 == 0
        for column, value in enumerate(values, start=1):
            is_text_column = column - 1 in text_columns
            style = (5 if alternate else 4) if is_text_column else (3 if alternate else 2)
            attributes = {"r": f"{_column_name(column)}{row_number}", "s": str(style)}
            if isinstance(value, (int, float)) and not isinstance(value, bool) and not is_text_column:
                cell = ET.SubElement(row, f"{{{SHEET_NS}}}c", **attributes)
                ET.SubElement(cell, f"{{{SHEET_NS}}}v").text = str(value)
            else:
                cell = ET.SubElement(row, f"{{{SHEET_NS}}}c", t="inlineStr", **attributes)
                inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
                ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = "" if value is None else str(value)

    if report:
        footer_row = ET.SubElement(sheet_data, f"{{{SHEET_NS}}}row", r=str(final_row), ht="21", customHeight="1")
        footer_cell = ET.SubElement(footer_row, f"{{{SHEET_NS}}}c", r=f"A{final_row}", s="10", t="inlineStr")
        inline = ET.SubElement(footer_cell, f"{{{SHEET_NS}}}is")
        ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = "Confidential — For authorized institutional use only."

    ET.SubElement(root, f"{{{SHEET_NS}}}autoFilter", ref=f"A{heading_row}:{final_column}{data_final_row}")
    if report:
        merged = ET.SubElement(root, f"{{{SHEET_NS}}}mergeCells", count="7")
        for number in (*range(1, 7), final_row):
            ET.SubElement(merged, f"{{{SHEET_NS}}}mergeCell", ref=f"A{number}:{final_column}{number}")
    ET.SubElement(root, f"{{{SHEET_NS}}}pageMargins", left="0.4", right="0.4", top="0.6", bottom="0.6", header="0.3", footer="0.3")
    if report:
        print_footer = ET.SubElement(root, f"{{{SHEET_NS}}}headerFooter")
        ET.SubElement(print_footer, f"{{{SHEET_NS}}}oddFooter").text = "&LSYS — Strengthen Your Skills&CConfidential&RPage &P of &N"
    return _xml(root)


def _core_properties(title: str) -> bytes:
    root = ET.Element(f"{{{CORE_NS}}}coreProperties")
    ET.SubElement(root, f"{{{DC_NS}}}title").text = title
    ET.SubElement(root, f"{{{DC_NS}}}creator").text = "SYS — Strengthen Your Skills"
    ET.SubElement(root, f"{{{CORE_NS}}}lastModifiedBy").text = "SYS Administrator"
    created = ET.SubElement(root, f"{{{DCTERMS_NS}}}created", {f"{{{XSI_NS}}}type": "dcterms:W3CDTF"})
    created.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _xml(root)


def build_master_workbook(
    *,
    title: str,
    headers: list[str],
    rows: list[list[object]],
    text_columns: set[int],
    report: dict[str, str] | None = None,
) -> bytes:
    """Create an XLSX workbook while retaining identifiers and contacts as text."""

    sheet_name = title[:31]
    output = io.BytesIO()
    document_relation = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types())
        package.writestr("_rels/.rels", _relationships((
            ("rId1", f"{document_relation}/officeDocument", "xl/workbook.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", f"{document_relation}/extended-properties", "docProps/app.xml"),
        )))
        package.writestr("xl/workbook.xml", _workbook(sheet_name))
        package.writestr("xl/_rels/workbook.xml.rels", _relationships((
            ("rId1", f"{document_relation}/worksheet", "worksheets/sheet1.xml"),
            ("rId2", f"{document_relation}/styles", "styles.xml"),
        )))
        package.writestr("xl/worksheets/sheet1.xml", _worksheet(headers, rows, text_columns, report))
        package.writestr("xl/styles.xml", _styles())
        package.writestr("docProps/core.xml", _core_properties(title))
        package.writestr("docProps/app.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>SYS — Strengthen Your Skills</Application></Properties>')
    return output.getvalue()
