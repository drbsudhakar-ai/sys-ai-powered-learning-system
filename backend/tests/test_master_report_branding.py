"""Regression checks for branded, administrator-readable SYS Excel reports."""

from __future__ import annotations

from io import BytesIO
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from app.services.master_spreadsheet import SHEET_NS, build_master_workbook


class MasterReportBrandingTests(unittest.TestCase):
    def _workbook(self, rows=None):
        return build_master_workbook(
            title="SYS Student Master",
            headers=["Roll Number", "Name", "Email", "Mobile", "Programme", "Admission Year"],
            rows=rows if rows is not None else [[
                "240334524681001", "AVUTI VIKAS", "student@example.com",
                "+918639228255", "B.Sc.(MPCS)", 2024,
            ]],
            text_columns={0, 3},
            report={
                "title": "STUDENT MASTER REPORT",
                "generated_at": "23 Aug 2026, 08:15:42 PM IST",
                "generated_by": "SYS Administrator",
                "summary": "Total records: 1    |    Active: 1    |    Pending registration: 0    |    Inactive: 0",
                "filters": "College: MJPTBCWRDC-Narayanpet",
            },
        )

    def _worksheet(self, workbook):
        with ZipFile(BytesIO(workbook)) as package:
            return ET.fromstring(package.read("xl/worksheets/sheet1.xml"))

    def _cell_text(self, worksheet, reference):
        cell = worksheet.find(f".//{{{SHEET_NS}}}c[@r='{reference}']")
        return cell.find(f"{{{SHEET_NS}}}is/{{{SHEET_NS}}}t").text

    def test_report_displays_sys_brand_tagline_and_title(self):
        worksheet = self._worksheet(self._workbook())
        self.assertEqual(self._cell_text(worksheet, "A1"), "SYS — Strengthen Your Skills")
        self.assertEqual(self._cell_text(worksheet, "A2"), "Shape Your Successful Future")
        self.assertEqual(self._cell_text(worksheet, "A3"), "STUDENT MASTER REPORT")

    def test_report_displays_ist_timestamp_administrator_summary_and_filters(self):
        worksheet = self._worksheet(self._workbook())
        self.assertIn("23 Aug 2026, 08:15:42 PM IST", self._cell_text(worksheet, "A4"))
        self.assertIn("SYS Administrator", self._cell_text(worksheet, "A4"))
        self.assertIn("Total records: 1", self._cell_text(worksheet, "A5"))
        self.assertIn("MJPTBCWRDC-Narayanpet", self._cell_text(worksheet, "A6"))

    def test_report_freezes_heading_and_filters_only_the_data_table(self):
        worksheet = self._worksheet(self._workbook())
        pane = worksheet.find(f".//{{{SHEET_NS}}}pane")
        self.assertEqual(pane.attrib["ySplit"], "8")
        self.assertEqual(pane.attrib["topLeftCell"], "A9")
        self.assertEqual(worksheet.find(f"{{{SHEET_NS}}}autoFilter").attrib["ref"], "A8:F9")
        self.assertEqual(self._cell_text(worksheet, "A8"), "Roll Number")

    def test_report_preserves_exact_roll_number_mobile_and_numeric_year(self):
        worksheet = self._worksheet(self._workbook())
        self.assertEqual(self._cell_text(worksheet, "A9"), "240334524681001")
        self.assertEqual(self._cell_text(worksheet, "D9"), "+918639228255")
        year = worksheet.find(f".//{{{SHEET_NS}}}c[@r='F9']")
        self.assertNotIn("t", year.attrib)
        self.assertEqual(year.find(f"{{{SHEET_NS}}}v").text, "2024")

    def test_report_has_visible_confidentiality_notice_and_print_footer(self):
        worksheet = self._worksheet(self._workbook())
        self.assertIn("authorized institutional use only", self._cell_text(worksheet, "A11"))
        footer = worksheet.find(f"{{{SHEET_NS}}}headerFooter/{{{SHEET_NS}}}oddFooter")
        self.assertIn("Confidential", footer.text)

    def test_report_has_blue_and_royal_purple_branding(self):
        with ZipFile(BytesIO(self._workbook())) as package:
            styles = package.read("xl/styles.xml").decode("utf-8")
        self.assertIn("FF082A66", styles)
        self.assertIn("FF6333A0", styles)

    def test_empty_report_keeps_branding_filters_and_confidentiality(self):
        worksheet = self._worksheet(self._workbook([]))
        self.assertEqual(worksheet.find(f"{{{SHEET_NS}}}autoFilter").attrib["ref"], "A8:F8")
        self.assertIn("authorized institutional use only", self._cell_text(worksheet, "A10"))


if __name__ == "__main__":
    unittest.main()
