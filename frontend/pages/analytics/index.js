import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getCourses,
  getFacultyAnalyticsAttention,
  getFacultyAnalyticsInterventions,
  getFacultyAnalyticsOverview,
  getFacultyAnalyticsTopics,
  getFacultyCourseBalance,
  getMe,
  notifyFacultyAttention,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

export default function FacultyLearningIntelligencePage() {
  const [me, setMe] = useState(null);
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [overview, setOverview] = useState(null);
  const [topics, setTopics] = useState(null);
  const [attention, setAttention] = useState(null);
  const [interventions, setInterventions] = useState(null);
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async (cid) => {
    const [ov, tp, att, iv, bal] = await Promise.all([
      getFacultyAnalyticsOverview(cid),
      getFacultyAnalyticsTopics(cid),
      getFacultyAnalyticsAttention(cid),
      getFacultyAnalyticsInterventions(cid),
      getFacultyCourseBalance(cid),
    ]);
    setOverview(ov.data);
    setTopics(tp.data);
    setAttention(att.data);
    setInterventions(iv.data);
    setBalance(bal.data);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const m = await getMe();
        setMe(m.data);
        const role = (m.data.role || "").toLowerCase();
        if (role === "student") {
          setError("Faculty/admin access required. Students: /analytics/me");
          return;
        }
        if (role === "admin") {
          // Admin may use this course view or /analytics/admin
        }
        const crs = await getCourses();
        setCourses(crs.data || []);
        if (crs.data?.[0]) {
          setCourseId(String(crs.data[0].id));
          await load(crs.data[0].id);
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const onNotify = async () => {
    try {
      setMessage("");
      const res = await notifyFacultyAttention(Number(courseId));
      setMessage(`Emitted ${res.data.emitted} attention notification(s).`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="sys-tagline !text-left !text-base">Faculty</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Learning Intelligence</h1>
        </div>
        {(me?.role || "").toLowerCase() === "admin" ? (
          <Link href="/analytics/admin" className="text-sm text-[var(--sys-blue)] underline">
            Institution view
          </Link>
        ) : null}
      </div>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}
      {message ? <p className="mt-3 text-green-700">{message}</p> : null}

      <label className="mt-4 block text-sm">
        Course
        <select
          className="input-field ml-2"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            if (e.target.value) await load(Number(e.target.value));
          }}
        >
          <option value="">Select…</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
      </label>

      {overview ? (
        <section className="mt-6">
          <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Class Overview</h2>
          <ul className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <li>Students: {overview.total_students}</li>
            <li>Active learning gaps: {overview.active_learning_gaps}</li>
            <li>Improving students: {overview.improving_students}</li>
            <li>Requiring attention: {overview.students_requiring_attention}</li>
            <li>
              Reassessments completed: {overview.reassessment_outcomes?.completed ?? 0} (mastered events:{" "}
              {overview.reassessment_outcomes?.mastered_events ?? 0})
            </li>
            <li>
              Interventions completed: {overview.remediation_outcomes?.interventions_completed ?? 0} /{" "}
              {overview.remediation_outcomes?.interventions_assigned ?? 0}
            </li>
          </ul>
          <p className="mt-2 text-xs text-[var(--sys-gray)]">
            Mastery distribution:{" "}
            {Object.entries(overview.mastery_distribution || {})
              .map(([k, v]) => `${k}=${v}`)
              .join(" · ") || "—"}
          </p>
        </section>
      ) : null}

      {balance ? (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Subject imbalance</h2>
          <p className="mt-1 text-xs text-[var(--sys-gray)]">{balance.note}</p>
          <p className="mt-2 text-sm">
            {Object.entries(balance.status_counts || {})
              .map(([k, v]) => `${k.replaceAll("_", " ")}=${v}`)
              .join(" · ")}
          </p>
          <ul className="mt-3 space-y-2">
            {(balance.students_needing_attention || []).map((s) => (
              <li key={s.student_id} className="sys-card !max-w-none text-sm">
                <p className="font-semibold">
                  {s.student_name || s.student_id} · {(s.balance_status || "").replaceAll("_", " ")}
                </p>
                <p>{s.reason}</p>
                {s.lagging_subject?.subject_name ? (
                  <p className="text-[var(--sys-gray)]">Lagging: {s.lagging_subject.subject_name}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Topic Analytics</h2>
        <ul className="mt-3 space-y-2">
          {(topics?.topics || []).map((t) => (
            <li key={t.topic_id} className="sys-card !max-w-none text-sm">
              <p className="font-semibold">{t.topic_name}</p>
              <p>
                Assessed {t.students_assessed} · Mastered {t.students_mastered} · Developing{" "}
                {t.students_developing} · Needs remediation {t.students_needing_remediation} · Persistent gaps{" "}
                {t.persistent_gap_count} · Trend {t.improvement_trend}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Student Attention</h2>
          <button type="button" className="btn-secondary text-sm" onClick={onNotify} disabled={!courseId}>
            Notify attention signals
          </button>
        </div>
        <ul className="mt-3 space-y-3">
          {(attention?.items || []).map((a, i) => (
            <li key={`${a.student_id}-${a.topic_id}-${i}`} className="sys-card !max-w-none text-sm">
              <p className="font-semibold">
                {a.student_name || `Student ${a.student_id}`} · {a.topic_name} · {a.severity}
              </p>
              <p>{a.reason}</p>
              <p className="mt-1 text-[var(--sys-gray)]">
                Recommended: {a.recommended_action?.message || "—"}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Remediation Effectiveness</h2>
        <p className="text-xs text-[var(--sys-gray)]">{interventions?.caveat}</p>
        <p className="mt-2 text-sm">
          Followed by mastery: {interventions?.summary?.followed_by_mastery_count ?? 0} · Associated with
          persistent gap: {interventions?.summary?.associated_with_persistent_gap_count ?? 0}
        </p>
      </section>
    </div>
  );
}
