import { useEffect, useState } from "react";
import Link from "next/link";
import {
  downloadAnalyzerReportPdf,
  getApiErrorMessage,
  getCourses,
  getMe,
  getMyPerformance,
} from "../src/api";
import { clearSession, getToken, redirectToLogin } from "../src/auth";

export default function MyPerformancePage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [data, setData] = useState(null);
  const [me, setMe] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const m = await getMe();
        setMe(m.data);
        if ((m.data.role || "").toLowerCase() !== "student") {
          setError("Student dashboard — staff should use Performance.");
        }
        const crs = await getCourses();
        setCourses(crs.data || []);
        if (crs.data?.[0]) setCourseId(String(crs.data[0].id));
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const load = async () => {
    setError("");
    try {
      const res = await getMyPerformance(courseId);
      setData(res.data);
    } catch (err) {
      setData(null);
      setError(getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    if (courseId && me && (me.role || "").toLowerCase() === "student") load();
  }, [courseId, me]);

  const download = async () => {
    if (!me) return;
    try {
      const res = await downloadAnalyzerReportPdf(me.id, courseId);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `sys_performance_report_c${courseId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const overall = data?.overall || {};
  const readiness = data?.readiness || {};

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Student</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">My Performance</h1>
      {error && <p className="sys-card mt-4 text-red-600" role="alert">{error}</p>}

      <div className="sys-card mt-4 !max-w-none flex flex-wrap gap-3 items-end">
        <label className="text-sm">
          Course
          <select className="mt-1 block rounded border px-2 py-1" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </label>
        <button type="button" className="btn-secondary" onClick={load}>Refresh</button>
        <button type="button" className="btn-primary" onClick={download} disabled={!data}>Download Report</button>
      </div>

      {data && (
        <>
          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Overall</h2>
            <p className="mt-2 text-3xl font-bold">{overall.average_percentage ?? "—"}%</p>
            <p className="text-sm text-[var(--sys-gray)]">
              Status: {overall.trend || "—"} · Accuracy: {overall.accuracy ?? "—"}% · Assessments: {overall.total_assessments}
            </p>
            <p className="mt-2 text-sm">Exam readiness estimate: <strong>{readiness.overall_estimate ?? "—"}%</strong></p>
            <p className="mt-1 text-xs text-[var(--sys-gray)]">{readiness.disclaimer}</p>
          </section>

          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Strong Areas</h2>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {(data.strengths || []).slice(0, 8).map((s) => (
                <li key={`${s.scope_type}-${s.name}`}>{s.name} ({s.classification})</li>
              ))}
              {!data.strengths?.length && <li className="text-[var(--sys-gray)]">None identified yet</li>}
            </ul>
          </section>

          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Needs Attention</h2>
            <ul className="mt-2 space-y-2 text-sm">
              {(data.high_priority_gaps || data.learning_gaps || []).slice(0, 8).map((g) => (
                <li key={`${g.scope_type}-${g.name}`} className="border-b pb-2">
                  <span className="font-semibold">{g.name}</span> — {g.classification}
                  <span className="block text-xs text-[var(--sys-gray)]">
                    Observed: accuracy {g.observed_evidence?.accuracy ?? "—"}% · {g.observed_evidence?.questions || 0} questions
                  </span>
                  <span className="block text-xs italic text-[var(--sys-gray)]">
                    Inference: {(g.system_inference?.signals || []).join(", ") || "—"}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Assessment-type performance</h2>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {(data.assessment_type_performance || []).map((r) => (
                <li key={r.assessment_type}>
                  {r.assessment_type}: {r.average_percentage ?? "—"}% (n={r.count}, trend={r.trend || "—"})
                </li>
              ))}
            </ul>
          </section>

          <section className="sys-card mt-4 !max-w-none">
            <h2 className="font-bold text-[var(--sys-blue)]">Priority Focus</h2>
            <ol className="mt-2 list-decimal pl-5 text-sm">
              {(data.recommended_focus || []).map((r) => (
                <li key={r.name}>{r.name} ({r.classification})</li>
              ))}
            </ol>
          </section>
        </>
      )}

      <p className="mt-6 text-sm">
        <Link href="/student/assessments" className="text-[var(--sys-blue)] hover:underline">My Assessments</Link>
      </p>
    </div>
  );
}
