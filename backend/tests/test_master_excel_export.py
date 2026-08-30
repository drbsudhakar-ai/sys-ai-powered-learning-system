"""Regression coverage for readable, Excel-safe SYS master exports."""

from __future__ import annotations

from io import BytesIO
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from app.services.master_spreadsheet import SHEET_NS, build_master_workbook


class MasterExcelExportTests(unittest.TestCase):
    def _workbook(self, rows=None):
        return build_master_workbook(
            title="SYS Student Master",
            headers=["Roll Number", "Name", "Email", "Mobile", "Programme", "Admission Year"],
            rows=rows if rows is not None else [[
                "240334524681001",
                "AVUTI VIKAS",
                "student@example.com",
                "••••••8255",
                "B.Sc.(MPCS)",
                2024,
            ]],
            text_columns={0, 3},
        )

    def _worksheet(self, workbook):
        with ZipFile(BytesIO(workbook)) as package:
            return ET.fromstring(package.read("xl/worksheets/sheet1.xml"))

    def _cell(self, worksheet, reference):
        return worksheet.find(f".//{{{SHEET_NS}}}c[@r='{reference}']")

    def _inline_value(self, cell):
        return cell.find(f"{{{SHEET_NS}}}is/{{{SHEET_NS}}}t").text

    def test_workbook_contains_required_excel_parts(self):
        with ZipFile(BytesIO(self._workbook())) as package:
            names = set(package.namelist())
            self.assertTrue({"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/styles.xml"}.issubset(names))

    def test_long_roll_number_is_saved_as_exact_text(self):
        cell = self._cell(self._worksheet(self._workbook()), "A2")
        self.assertEqual(cell.attrib["t"], "inlineStr")
        self.assertIn(cell.attrib["s"], {"4", "5"})
        self.assertEqual(self._inline_value(cell), "240334524681001")

    def test_masked_mobile_renders_as_valid_unicode_text(self):
        cell = self._cell(self._worksheet(self._workbook()), "D2")
        self.assertEqual(cell.attrib["t"], "inlineStr")
        self.assertEqual(self._inline_value(cell), "••••••8255")

    def test_academic_year_remains_a_number(self):
        cell = self._cell(self._worksheet(self._workbook()), "F2")
        self.assertNotIn("t", cell.attrib)
        self.assertEqual(cell.find(f"{{{SHEET_NS}}}v").text, "2024")

    def test_formula_like_values_are_plain_text_not_executable_formulas(self):
        worksheet = self._worksheet(self._workbook([["001234", "=2+3", "name@example.com", "+919876543210", "B.Sc", 2024]]))
        self.assertEqual(self._inline_value(self._cell(worksheet, "B2")), "=2+3")
        self.assertEqual(self._inline_value(self._cell(worksheet, "D2")), "+919876543210")
        self.assertIsNone(worksheet.find(f".//{{{SHEET_NS}}}f"))

    def test_header_is_frozen_and_filters_are_available(self):
        worksheet = self._worksheet(self._workbook())
        pane = worksheet.find(f".//{{{SHEET_NS}}}pane")
        self.assertEqual(pane.attrib["state"], "frozen")
        self.assertEqual(worksheet.find(f"{{{SHEET_NS}}}autoFilter").attrib["ref"], "A1:F2")

    def test_sys_brand_and_text_format_exist_in_styles(self):
        with ZipFile(BytesIO(self._workbook())) as package:
            styles = package.read("xl/styles.xml").decode("utf-8")
            properties = package.read("docProps/core.xml").decode("utf-8")
        self.assertIn("FF082A66", styles)
        self.assertIn('numFmtId="49"', styles)
        self.assertIn("Strengthen Your Skills", properties)

    def test_empty_export_still_has_a_valid_header(self):
        worksheet = self._worksheet(self._workbook([]))
        self.assertEqual(self._inline_value(self._cell(worksheet, "A1")), "Roll Number")
        self.assertEqual(worksheet.find(f"{{{SHEET_NS}}}autoFilter").attrib["ref"], "A1:F1")


if __name__ == "__main__":
    unittest.main()
