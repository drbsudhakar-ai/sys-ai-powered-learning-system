import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAdminAnalyticsAttention,
  getAdminAnalyticsCourses,
  getAdminAnalyticsOverview,
  getAdminAnalyticsSubjects,
  getAdminAnalyticsTrends,
  getAdminCourseBalance,
  getApiErrorMessage,
  getCourses,
  getMe,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

export default function AdminLearningIntelligencePage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [overview, setOverview] = useState(null);
  const [courseRows, setCourseRows] = useState(null);
  const [subjects, setSubjects] = useState(null);
  const [trends, setTrends] = useState(null);
  const [attention, setAttention] = useState(null);
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState("");

  const load = async (cid) => {
    const params = cid ? { course_id: cid } : {};
    const [ov, crs, tr, att, bal] = await Promise.all([
      getAdminAnalyticsOverview(params),
      getAdminAnalyticsCourses(),
      getAdminAnalyticsTrends(params),
      getAdminAnalyticsAttention(params),
      getAdminCourseBalance(params),
    ]);
    setOverview(ov.data);
    setCourseRows(crs.data);
    setTrends(tr.data);
    setAttention(att.data);
    setBalance(bal.data);
    if (cid) {
      const sub = await getAdminAnalyticsSubjects(cid);
      setSubjects(sub.data);
    } else {
      setSubjects(null);
    }
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if ((me.data.role || "").toLowerCase() !== "admin") {
          setError("Admin access required.");
          return;
        }
        const crs = await getCourses();
        setCourses(crs.data || []);
        await load("");
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const totals = overview?.totals || {};

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="sys-tagline !text-left !text-base">Admin</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Institution Learning Intelligence</h1>
        </div>
        <Link href="/analytics" className="text-sm text-[var(--sys-blue)] underline">
          Course faculty view
        </Link>
      </div>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}

      <label className="mt-4 block text-sm">
        Filter course (optional)
        <select
          className="input-field ml-2"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            await load(e.target.value ? Number(e.target.value) : "");
          }}
        >
          <option value="">All courses</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
      </label>

      <section className="mt-6">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Overall KPIs</h2>
        <ul className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
          <li>Assessment attempts: {totals.assessment_participation_attempts ?? 0}</li>
          <li>Active learning gaps: {totals.active_learning_gaps ?? 0}</li>
          <li>Mastered topic states: {totals.mastered_topic_states ?? 0}</li>
          <li>Persistent gap proxy: {totals.persistent_gap_proxy ?? 0}</li>
          <li>Remediation demand: {totals.remediation_demand_interventions ?? 0}</li>
          <li>Intervention completion: {totals.intervention_completion ?? 0}</li>
          <li>
            Reassessment completed: {totals.reassessment_completed ?? 0} / {totals.reassessment_started ?? 0}
          </li>
        </ul>
        <p className="mt-2 text-xs text-[var(--sys-gray)]">
          Mastery distribution:{" "}
          {Object.entries(totals.mastery_distribution || {})
            .map(([k, v]) => `${k}=${v}`)
            .join(" · ") || "—"}
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Course Trends</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {(courseRows?.courses || []).slice(0, 20).map((c) => (
            <li key={c.course_id} className="sys-card !max-w-none">
              <strong>{c.title}</strong> — gaps {c.totals?.active_learning_gaps ?? 0}, mastered states{" "}
              {c.totals?.mastered_topic_states ?? 0}, reassessment completed{" "}
              {c.totals?.reassessment_completed ?? 0}
            </li>
          ))}
        </ul>
      </section>

      {balance ? (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Course balance</h2>
          <p className="mt-1 text-xs text-[var(--sys-gray)]">{balance.note}</p>
          <ul className="mt-2 space-y-2 text-sm">
            {(balance.courses || []).map((c) => (
              <li key={c.course_id} className="sys-card !max-w-none">
                <strong>{c.course_title}</strong> — attention {c.attention_count}
                <span className="ml-2 text-[var(--sys-gray)]">
                  {Object.entries(c.status_counts || {})
                    .map(([k, v]) => `${k.replaceAll("_", " ")}=${v}`)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {subjects ? (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Subject Trends</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {(subjects.subjects || []).map((s) => (
              <li key={s.subject_id}>
                {s.name}:{" "}
                {Object.entries(s.mastery_distribution || {})
                  .map(([k, v]) => `${k}=${v}`)
                  .join(", ") || "no mastery states"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Mastery Event Trends</h2>
        <p className="text-sm">
          {Object.entries(trends?.event_counts || {})
            .map(([k, v]) => `${k}=${v}`)
            .join(" · ") || "—"}
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Attention Signals</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {(attention?.items || []).slice(0, 30).map((a, i) => (
            <li key={i} className="sys-card !max-w-none">
              Course {a.course_id} · {a.student_name || a.student_id} · {a.topic_name} · {a.severity}
              <p className="text-[var(--sys-gray)]">{a.reason}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
