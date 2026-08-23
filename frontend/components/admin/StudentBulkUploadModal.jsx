import React, { useState } from "react";
import * as XLSX from "xlsx";
import BulkUploadSummary from "./BulkUploadSummary";

export default function StudentBulkUploadModal({ onClose }) {
  const [rows, setRows] = useState([]);
  const [errors, setErrors] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

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
          !row.roll_number ||
          !row.name ||
          !row.email ||
          !row.mobile_number ||
          !row.college ||
          !row.department ||
          !row.academic_program ||
          !row.admission_year ||
          !row.present_year ||
          !row.academic_status
        ) {
          errorRows.push({ idx, reason: "Missing mandatory fields" });
        } else if (!/^\S+@\S+\.\S+$/.test(row.email)) {
          errorRows.push({ idx, reason: "Invalid email format" });
        } else {
          validRows.push({ ...row, role: "student" });
        }
      });

      setRows(validRows);
      setErrors(errorRows);
    };

    reader.readAsArrayBuffer(file);
  };

  const handleConfirm = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/students/bulk`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(rows),
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const result = await response.json();
      setUploadResult(result);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadResult({ status: "error", message: err.message });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-5xl overflow-hidden">
        {!uploadResult ? (
          <>
            {/* Header */}
            <div className="bg-blue-600 text-white px-6 py-3">
              <h2 className="text-lg font-semibold">Bulk Upload Students</h2>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              <input type="file" accept=".csv,.xlsx" onChange={handleFileUpload} />
              <a href="/templates/student_upload_template.csv" download>
                Download Student Template
              </a>

              {/* Preview table */}
              <h3>Preview</h3>
              <table border="2" className="text-center">
                <thead className="text-center">
                  <tr className="border-b border-gray-300 bg-gray-100">
                    <th>Roll Number</th><th>Name</th><th>Email</th><th>Mobile</th>
                    <th>College</th><th>Department</th><th>Academic Program</th>
                    <th>Admission Year</th><th>Present Year</th><th>Academic Status</th>
                  </tr>
                </thead>
                <tbody border="2" className="text-center">
                  {rows.map((r, i) => (
                    <tr key={i} border="2" className="border-b border-gray-300">
                      <td>{r.roll_number}</td>
                      <td>{r.name}</td>
                      <td>{r.email}</td>
                      <td>{r.mobile_number}</td>
                      <td>{r.college}</td>
                      <td>{r.department}</td>
                      <td>{r.academic_program}</td>
                      <td>{r.admission_year}</td>
                      <td>{r.present_year}</td>
                      <td>{r.academic_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {errors.length > 0 && (
                <div className="mt-4">
                  <h4>Errors</h4>
                  <ul>
                    {errors.map((e, i) => (
                      <li key={i}>Row {e.idx + 2}: {e.reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 border-t px-6 py-4 bg-gray-50">
              <button onClick={onClose}>Cancel</button>
              <button onClick={handleConfirm}>Confirm Upload</button>
            </div>
          </>
        ) : (
          <BulkUploadSummary result={uploadResult} onClose={onClose} />
        )}
      </div>
    </div>
  );
}
