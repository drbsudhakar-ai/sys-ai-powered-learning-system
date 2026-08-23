import React, { useState } from "react";
import * as XLSX from "xlsx";

export default function FacultyBulkUploadModal({ onClose }) {
  const [rows, setRows] = useState([]);
  const [errors, setErrors] = useState([]);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();

    reader.onload = (evt) => {
      const data = new Uint8Array(evt.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const parsed = XLSX.utils.sheet_to_json(sheet);

      const validRows = [];
      const errorRows = [];

      parsed.forEach((row, idx) => {
        if (
          !row.employee_code ||
          !row.name ||
          !row.email ||
          !row.mobile_number ||
          !row.college ||
          !row.department ||
          !row.designation ||
          !row.employment_status
        ) {
          errorRows.push({ idx, reason: "Missing mandatory fields" });
        } else if (!/^\S+@\S+\.\S+$/.test(row.email)) {
          errorRows.push({ idx, reason: "Invalid email format" });
        } else {
          validRows.push({ ...row, role: "faculty" });
        }
      });

      setRows(validRows);
      setErrors(errorRows);
    };

    reader.readAsArrayBuffer(file);
  };

  const handleConfirm = async () => {
    for (const faculty of rows) {
      await fetch("/api/faculty", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(faculty),
      });
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-4xl overflow-hidden">
        {/* Header */}
        <div className="bg-orange-600 text-white px-6 py-3">
          <h2 className="text-lg font-semibold">Bulk Upload Faculty</h2>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileUpload}
            className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4
                       file:rounded-full file:border-0 file:text-sm file:font-semibold
                       file:bg-orange-50 file:text-orange-700 hover:file:bg-orange-100"
          />

          <a
            href="/templates/faculty_upload_template.csv"
            download
            className="text-orange-600 hover:underline text-sm"
          >
            Download Faculty Template
          </a>

          <h3 className="text-md font-semibold text-gray-800">Preview</h3>
          <div className="border rounded overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="border px-2 py-1">Employee Code</th>
                  <th className="border px-2 py-1">Name</th>
                  <th className="border px-2 py-1">Email</th>
                  <th className="border px-2 py-1">Mobile</th>
                  <th className="border px-2 py-1">College</th>
                  <th className="border px-2 py-1">Department</th>
                  <th className="border px-2 py-1">Designation</th>
                  <th className="border px-2 py-1">Employment Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td className="border px-2 py-1">{r.employee_code}</td>
                    <td className="border px-2 py-1">{r.name}</td>
                    <td className="border px-2 py-1">{r.email}</td>
                    <td className="border px-2 py-1">{r.mobile_number}</td>
                    <td className="border px-2 py-1">{r.college}</td>
                    <td className="border px-2 py-1">{r.department}</td>
                    <td className="border px-2 py-1">{r.designation}</td>
                    <td className="border px-2 py-1">{r.employment_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {errors.length > 0 && (
            <div className="bg-red-50 border border-red-300 text-red-700 rounded p-3">
              <h4 className="font-semibold mb-2">Errors</h4>
              <ul className="list-disc list-inside text-sm">
                {errors.map((e, i) => (
                  <li key={i}>Row {e.idx + 2}: {e.reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t px-6 py-4 bg-gray-50">
          <button onClick={onClose} className="px-4 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300">
            Cancel
          </button>
          <button onClick={handleConfirm} className="px-4 py-2 rounded bg-orange-600 text-white hover:bg-orange-700">
            Confirm Upload
          </button>
        </div>
      </div>
    </div>
  );
}
