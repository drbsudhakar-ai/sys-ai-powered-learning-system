import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminListStudents,
  downloadAnalyzerReportPdf,
  getApiErrorMessage,
  getCourseAttention,
  getCourses,
  getMe,
  getPerformanceAnalysis,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function StaffStudentPerformancePage() {
  const router = useRouter();
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [attention, setAttention] = useState(null);
  const [error, setError] = useState("");

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
        if (router.query.course_id) setCourseId(String(router.query.course_id));
        if (router.query.student_id) setStudentId(String(router.query.student_id));
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.query.course_id, router.query.student_id]);

  const load = async () => {
    setError("");
    try {
      const [a, att] = await Promise.all([
        getPerformanceAnalysis(studentId, courseId, { refresh: true }),
        getCourseAttention(courseId).catch(() => ({ data: null })),
      ]);
      setAnalysis(a.data);
      setAttention(att.data);
    } catch (err) {
      setAnalysis(null);
      setError(getApiErrorMessage(err));
    }
  };

  const download = async () => {
    try {
      const res = await downloadAnalyzerReportPdf(studentId, courseId);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `sys_performance_report_s${studentId}_c${courseId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <Link href="/performance" className="text-sm font-semibold text-[var(--sys-blue)] hover:underline">
        ← Performance sheet
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-[var(--sys-blue)]">Student Performance Analyzer</h1>
      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}

      <div className="sys-card mt-4 !max-w-none flex flex-wrap gap-3 items-end">
        <label className="text-sm">
          Course
          <select className="mt-1 block rounded border px-2 py-1" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">Select</option>
            {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Student
          <select className="mt-1 block rounded border px-2 py-1" value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            <option value="">Select</option>
            {students.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.roll_number || s.id})</option>)}
          </select>
        </label>
        <button type="button" className="btn-primary" disabled={!courseId || !studentId} onClick={load}>Analyze</button>
        <button type="button" className="btn-secondary" disabled={!analysis} onClick={download}>PDF Report</button>
      </div>

      {attention && (
        <section className="sys-card mt-4 !max-w-none text-sm">
          <h2 className="font-bold text-[var(--sys-blue)]">Course attention</h2>
          <p className="mt-1">Needs attention: {(attention.needs_attention || []).length}</p>
          <p>High performing: {(attention.high_performing || []).length}</p>
        </section>
      )}

      {analysis && (
        <>
          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Overall</h2>
            <p className="mt-2">{analysis.overall?.average_percentage}% · Trend {analysis.overall?.trend}</p>
            <p className="text-sm">Readiness estimate: {analysis.readiness?.overall_estimate}% ({analysis.readiness?.label})</p>
          </section>
          <section className="sys-card mt-4 !max-w-none text-sm">
            <h2 className="font-bold text-[var(--sys-blue)]">Subject / Topic / Difficulty</h2>
            <p className="mt-2 font-semibold">Subjects</p>
            <ul className="list-disc pl-5">
              {(analysis.subject_performance || []).map((s) => (
                <li key={s.id || s.name}>{s.name}: {s.percentage}% [{s.classification}]</li>
              ))}
            </ul>
            <p className="mt-3 font-semibold">Assessment types</p>
            <ul className="list-disc pl-5">
              {(analysis.assessment_type_performance || []).map((s) => (
                <li key={s.assessment_type}>{s.assessment_type}: {s.average_percentage ?? "—"}%</li>
              ))}
            </ul>
          </section>
          <section className="sys-card mt-4 !max-w-none text-sm">
            <h2 className="font-bold text-[var(--sys-blue)]">Learning gaps</h2>
            <ul className="mt-2 space-y-2">
              {(analysis.learning_gaps || []).slice(0, 15).map((g) => (
                <li key={`${g.scope_type}-${g.name}`}>
                  <strong>{g.name}</strong> {g.classification}
                  <span className="block text-xs">Evidence accuracy {g.observed_evidence?.accuracy}%</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
