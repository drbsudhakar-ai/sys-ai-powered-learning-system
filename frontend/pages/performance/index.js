import { useEffect, useState } from "react";
import Link from "next/link";
import {
  adminListStudents,
  downloadReportCardPdf,
  getApiErrorMessage,
  getCourses,
  getMe,
  getPerformanceSheet,
  getReportCard,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

function ResultTable({ title, rows }) {
  if (!rows?.length) {
    return (
      <section className="sys-card mt-4 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">{title}</h2>
        <p className="mt-2 text-sm text-[var(--sys-gray)]">No results yet.</p>
      </section>
    );
  }
  return (
    <section className="sys-card mt-4 !max-w-none overflow-x-auto">
      <h2 className="font-bold text-[var(--sys-blue)]">{title}</h2>
      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th>Test</th>
            <th>Date</th>
            <th>Marks</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.attempt_id} className="border-b">
              <td>{r.title}</td>
              <td>{r.date ? new Date(r.date).toLocaleDateString() : "—"}</td>
              <td>{r.marks_obtained}/{r.marks_available}</td>
              <td>{r.percentage ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function PerformancePage() {
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [sheet, setSheet] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Staff access required.");
          return;
        }
        const [crs, stu] = await Promise.all([getCourses(), adminListStudents().catch(() => ({ data: [] }))]);
        setCourses(crs.data || []);
        setStudents(stu.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const loadSheet = async () => {
    setError("");
    setLoading(true);
    setReport(null);
    try {
      const res = await getPerformanceSheet({ student_id: studentId, course_id: courseId });
      setSheet(res.data);
    } catch (err) {
      setSheet(null);
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const generateCard = async () => {
    setError("");
    try {
      const res = await getReportCard({ student_id: studentId, course_id: courseId });
      setReport(res.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const downloadPdf = async () => {
    setError("");
    try {
      const res = await downloadReportCardPdf({ student_id: studentId, course_id: courseId });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `sys_report_card_s${studentId}_c${courseId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to download PDF."));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Reporting</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Student Performance Sheet</h1>

      <div className="sys-card mt-6 !max-w-none grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="courseId" className="mb-1 block text-sm font-semibold">Course</label>
          <select id="courseId" className="input-field" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">Select…</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="studentId" className="mb-1 block text-sm font-semibold">Student</label>
          <select id="studentId" className="input-field" value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            <option value="">Select…</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.roll_number || s.email})</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button type="button" className="btn-primary" disabled={!courseId || !studentId || loading} onClick={loadSheet}>
            {loading ? "Loading…" : "Load Sheet"}
          </button>
        </div>
      </div>

      {error && <p className="sys-card mt-4 text-red-600" role="alert">{error}</p>}

      {sheet && (
        <>
          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Student</h2>
            <p className="text-sm">{sheet.student?.name} · {sheet.student?.roll_number || sheet.student?.id}</p>
            <p className="text-sm">Course: {sheet.course?.title}</p>
            <p className="mt-2 text-sm">
              Overall avg: {sheet.overall_summary?.average_percentage ?? "—"}% ·
              Assessments: {sheet.overall_summary?.total_assessments ?? 0}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" className="btn-primary" onClick={generateCard}>Generate Report Card</button>
              <button type="button" className="btn-secondary" onClick={downloadPdf}>Download PDF</button>
            </div>
          </section>

          <ResultTable title="Topic Tests" rows={sheet.topic_assessments} />
          <ResultTable title="Weekly Tests" rows={sheet.weekly_tests} />
          <ResultTable title="Monthly Tests" rows={sheet.monthly_tests} />
          <ResultTable title="Grand Tests" rows={sheet.grand_tests} />
          <ResultTable title="Final Grand Tests" rows={sheet.final_grand_tests} />

          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Subject Performance</h2>
            {(sheet.subject_summary || []).length === 0 ? (
              <p className="mt-2 text-sm text-[var(--sys-gray)]">No subject performance data yet.</p>
            ) : (
              <ul className="mt-2 list-disc pl-5 text-sm">
                {sheet.subject_summary.map((s) => (
                  <li key={s.subject}>{s.subject}: avg {s.average_percentage}% ({s.assessments_count})</li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {report && (
        <section className="sys-card mt-4 !max-w-none">
          <h2 className="font-bold text-[var(--sys-blue)]">Report Card Preview</h2>
          <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(report.overall_performance, null, 2)}</pre>
        </section>
      )}

      <p className="mt-6 text-sm">
        <Link href="/admin-dashboard" className="text-[var(--sys-blue)] no-underline hover:underline">← Admin Dashboard</Link>
      </p>
    </div>
  );
}
