"""Four-sheet syllabus contract; opaque, signed references are never hand-numbered."""
import hashlib
import hmac
import re
from copy import deepcopy
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from fastapi import HTTPException
from pydantic import ValidationError
from app.config import settings
from app.syllabus_schemas import Node
from app.services import syllabus_review as review
from app.services import master_spreadsheet as excel

SHEETS = {"Subjects": "subject", "Units": "unit", "Topics": "topic", "Subtopics": "subtopic"}
SEP = " / "


def package_xml(value):
    # Package roots have a single namespace. Use the conventional default form
    # for compatibility with stricter Office/OpenXML readers.
    match = re.search(rb'<(ns[0-9]+):', value)
    if not match: return value
    prefix = match.group(1)
    return value.replace(prefix + b':', b'').replace(b'xmlns:' + prefix + b'=', b'xmlns=')


def reference(proposal, key):
    message = f"syllabus-v2|{proposal.id}|{proposal.base_hash}|{key}"
    return key + "." + hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


def paths(nodes):
    result = {}
    for level in review.LEVELS:
        for n in nodes:
            if n["level"] == level:
                result[n["key"]] = (result[n["parent"]] + SEP if n["parent"] else "") + n["name"]
    return result


def contract(proposal, *, blank=False):
    nodes = [] if blank else proposal.proposed_nodes
    labels = paths(nodes)
    sheets = {}
    for name, level in SHEETS.items():
        rows = []
        for n in sorted(nodes, key=lambda n: (labels.get(n["parent"], ""), n["sequence"], n["name"])):
            if n["level"] != level: continue
            row = {"Name": n["name"], "Description": n["description"], "Order": n["sequence"]}
            if level != "subject": row["Parent"] = labels[n["parent"]]
            if level == "unit": row["Learning outcome"] = n["learning_outcome"]
            row["SYS Reference"] = reference(proposal, n["key"])
            rows.append(row)
        sheets[name] = rows
    return {"metadata": {"Format": "SYS-SYLLABUS-2", "Review": str(proposal.id),
            "Version": str(proposal.version), "Baseline": proposal.base_hash}, "sheets": sheets}


def parse(proposal, payload):
    expected = contract(proposal)["metadata"]
    if payload.metadata != expected:
        raise HTTPException(409, "This workbook belongs to another review or an older draft. Download the current workbook.")
    if set(payload.sheets) != set(SHEETS):
        raise HTTPException(422, "The workbook must contain Subjects, Units, Topics and Subtopics sheets")
    if sum(len(rows) for rows in payload.sheets.values()) > 5000:
        raise HTTPException(422, "Maximum 5,000 syllabus items per workbook")
    # Omitted rows are retained. Blank references explicitly mean new rows.
    existing = {n["key"]: deepcopy(n) for n in proposal.proposed_nodes}
    original_paths = paths(proposal.proposed_nodes)
    tokens = {reference(proposal, key): key for key in existing}
    seen, parsed, errors = set(), {}, []
    for sheet, level in SHEETS.items():
        available = {}
        current_paths = paths(list({**existing, **parsed}.values()))
        for key, n in {**existing, **parsed}.items():
            if level != "subject" and n["level"] == review.LEVELS[review.LEVELS.index(level)-1]:
                for label in {current_paths[key], original_paths.get(key)} - {None}:
                    available.setdefault(label, set()).add(key)
        for index, row in enumerate(payload.sheets[sheet], 2):
            label = f"{sheet}, row {index}"
            token = str(row.get("SYS Reference", "")).strip()
            key = tokens.get(token) if token else f"new:{uuid4().hex}"
            if not key or key in seen:
                errors.append(f"{label}: damaged or duplicate SYS reference"); continue
            seen.add(key)
            if token and existing[key]["level"] != level:
                errors.append(f"{label}: reference belongs to another sheet"); continue
            parent = None
            if level != "subject":
                choices = available.get(str(row.get("Parent", "")).strip(), set())
                if len(choices) != 1:
                    errors.append(f"{label}: parent is missing or ambiguous; select its complete path"); continue
                parent = next(iter(choices))
            try:
                order = row.get("Order")
                if isinstance(order, str) and order.strip().isdigit(): order = int(order.strip())
                node = Node(key=key, level=level, parent=parent, name=row.get("Name", ""),
                    description=row.get("Description", ""), learning_outcome=row.get("Learning outcome", ""), sequence=order)
                parsed[key] = node.model_dump()
            except ValidationError:
                errors.append(f"{label}: use a name (1–200 characters), descriptions up to 500 characters, and a positive whole-number order")
    if errors: raise HTTPException(422, {"errors": errors[:60]})
    desired = list({**existing, **parsed}.values())
    return review.validate_nodes(desired, proposal.base_nodes)


def build_workbook(proposal, course, *, blank=False):
    """Application export extends SYS's existing dependency-free Excel writer."""
    data = contract(proposal, blank=blank)
    ns = excel.SHEET_NS
    q = lambda name: f"{{{ns}}}{name}"
    definitions, worksheets = [], []
    instructions = [
        ["SYS - Strengthen Your Skills", "Shape Your Successful Future"],
        ["Course", course.title], ["Purpose", "Draft syllabus for review - NOT approved"],
        ["Editing", "Write each description once. Keep row 1 headers unchanged."],
        ["Parents", "Choose complete parent paths. After renaming a parent, validate its child references."],
        ["New rows", "Leave SYS Reference blank. Set a unique positive order within the parent."],
        ["Existing rows", "Hidden SYS references preserve identity. Never edit them."],
        ["Omitted rows", "Omitting a row does not delete the existing item."],
        ["Workflow", "Upload > validate preview > save draft > submit > coordinator approval."],
        ["Conflicts", "Download a fresh workbook after saving your draft or another approval."],
        ["Template", "Use Excel or LibreOffice. CSV and the old flat template are not accepted."],
    ]
    guide = ET.fromstring(excel._worksheet(["SYS Syllabus", "Guidance"], instructions, {0, 1}, None))
    for col in guide.find(q("cols")):
        col.set("width", "47" if col.get("min") == "1" else "95")
    for row in guide.find(q("sheetData")):
        row.set("ht", "40"); row.set("customHeight", "1")
        if row.get("r") != "1":
            for cell in row: cell.set("s", "11")
    worksheets.append(("Instructions", guide))
    for sheet, level in SHEETS.items():
        headers = ["Name", "Description", "Order"]
        if level != "subject": headers.append("Parent")
        if level == "unit": headers.append("Learning outcome")
        headers += ["SYS Reference", "SYS Path"]
        rows = [[row.get(h, "") for h in headers] for row in data["sheets"][sheet]]
        root = ET.fromstring(excel._worksheet(headers, rows, set(range(len(headers)))-{2}, None))
        columns = root.find(q("cols"))
        for col in list(columns): columns.remove(col)
        for idx, header in enumerate(headers, 1):
            attrs = dict(min=str(idx), max=str(idx), width="12" if header == "Order" else "45", customWidth="1", style="11")
            if header.startswith("SYS "): attrs.update(hidden="1", style="4")
            ET.SubElement(columns, q("col"), attrs)
        ref_column = len(headers)-1
        path_column = excel._column_name(len(headers))
        rows_element = root.find(q("sheetData"))
        # Prepare room for new rows, with dropdowns and computed parent paths.
        root.find(q("dimension")).set("ref", f"A1:{path_column}5001")
        present_rows = {int(r.get("r")): r for r in rows_element}
        for index in range(2, 5002):
            row = present_rows.get(index)
            if row is None: row = ET.SubElement(rows_element, q("row"), r=str(index))
            row.set("ht", "60"); row.set("customHeight", "1")
            for cell in row:
                # Existing reference is locked; all normal inputs are unlocked.
                if cell.get("r", "").startswith(excel._column_name(ref_column)):
                    cell.set("s", "4")
                else: cell.set("s", "11")
            address = f"{path_column}{index}"
            old = row.find(f"{q('c')}[@r='{address}']")
            if old is not None: row.remove(old)
            cell = ET.SubElement(row, q("c"), r=address, s="4")
            formula = f'IF(A{index}="","",A{index})' if level == "subject" else f'IF(A{index}="","",D{index}&" / "&A{index})'
            ET.SubElement(cell, q("f")).text = formula
        # Sheet protection intentionally permits insertion/filtering; signed references
        # and backend scope checks remain authoritative.
        protection = ET.Element(q("sheetProtection"), sheet="1", objects="1", scenarios="1", insertRows="0", autoFilter="0", sort="0", selectLockedCells="1")
        root.insert(list(root).index(rows_element)+1, protection)
        if level != "subject":
            validation = ET.Element(q("dataValidations"), count="1")
            item = ET.SubElement(validation, q("dataValidation"), type="list", allowBlank="0", showErrorMessage="1",
                errorTitle="Select a parent", error="Choose a complete parent path from the preceding sheet.", sqref="D2:D5001")
            ET.SubElement(item, q("formula1")).text = f"SYS_{list(SHEETS)[review.LEVELS.index(level)-1]}"
            margin = root.find(q("pageMargins")); root.insert(list(root).index(margin), validation)
        definitions.append((f"SYS_{sheet}", f"'{sheet}'!${path_column}$2:${path_column}$5001"))
        worksheets.append((sheet, root))
    meta = ET.fromstring(excel._worksheet(["Setting", "Value"], list(data["metadata"].items()), {0, 1}, None))
    worksheets.append(("SYS Metadata", meta))
    workbook = ET.Element(q("workbook"))
    sheets = ET.SubElement(workbook, q("sheets"))
    for index, (name, _) in enumerate(worksheets, 1):
        ET.SubElement(sheets, q("sheet"), {"name": name, "sheetId": str(index), f"{{{excel.REL_NS}}}id": f"rId{index}",
            **({"state": "veryHidden"} if name == "SYS Metadata" else {})})
    names = ET.SubElement(workbook, q("definedNames"))
    for name, formula in definitions: ET.SubElement(names, q("definedName"), name=name).text = formula
    ET.SubElement(workbook, q("calcPr"), fullCalcOnLoad="1")
    styles = ET.fromstring(excel._styles())
    xfs = styles.find(q("cellXfs"))
    unlocked = deepcopy(xfs[4]); unlocked.set("applyProtection", "1")
    ET.SubElement(unlocked, q("protection"), locked="0")
    alignment = unlocked.find(q("alignment"))
    if alignment is not None: alignment.set("wrapText", "1")
    xfs.append(unlocked); xfs.set("count", str(len(xfs)))
    types = ET.fromstring(excel._content_types())
    for index in range(2, len(worksheets)+1):
        ET.SubElement(types, f"{{{excel.CONTENT_NS}}}Override", PartName=f"/xl/worksheets/sheet{index}.xml",
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", package_xml(excel._xml(types)))
        package.writestr("_rels/.rels", package_xml(excel._relationships([
            ("rId1", f"{excel.REL_NS}/officeDocument", "xl/workbook.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", f"{excel.REL_NS}/extended-properties", "docProps/app.xml")])))
        package.writestr("docProps/core.xml", excel._core_properties("SYS Syllabus Review"))
        package.writestr("docProps/app.xml", '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>SYS</Application></Properties>')
        package.writestr("xl/workbook.xml", excel._xml(workbook))
        package.writestr("xl/_rels/workbook.xml.rels", package_xml(excel._relationships([
            *[(f"rId{i}", f"{excel.REL_NS}/worksheet", f"worksheets/sheet{i}.xml") for i in range(1, len(worksheets)+1)],
            ("rIdStyles", f"{excel.REL_NS}/styles", "styles.xml")])))
        package.writestr("xl/styles.xml", excel._xml(styles))
        for index, (_, root) in enumerate(worksheets, 1): package.writestr(f"xl/worksheets/sheet{index}.xml", excel._xml(root))
    return output.getvalue()
