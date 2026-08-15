import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getCourses,
  getMe,
  getMyAnalytics,
  getMyAnalyticsAttention,
  getMyAnalyticsTrends,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

const INDICATOR = {
  GREEN: "🟢",
  YELLOW: "🟡",
  ORANGE: "🟠",
  RED: "🔴",
  GRAY: "⚪",
};

export default function MyLearningIntelligencePage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [data, setData] = useState(null);
  const [trends, setTrends] = useState(null);
  const [attention, setAttention] = useState(null);
  const [error, setError] = useState("");

  const load = async (cid) => {
    const [main, tr, att] = await Promise.all([
      getMyAnalytics(cid),
      getMyAnalyticsTrends(cid),
      getMyAnalyticsAttention(cid),
    ]);
    setData(main.data);
    setTrends(tr.data);
    setAttention(att.data);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if ((me.data.role || "").toLowerCase() !== "student") {
          setError("Student access required. Staff: use /analytics");
          return;
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

  const summary = data?.summary || {};

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Student</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">My Learning Intelligence</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Insights from your mastery, practice, and learning gaps. Indicators come from the backend — not recalculated here.
      </p>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}

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

      {data ? (
        <>
          <section className="mt-6">
            <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Overall Learning Progress</h2>
            <ul className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
              <li>Mastered topics: {summary.mastered_topics ?? 0}</li>
              <li>Improving: {summary.improving_topics ?? 0}</li>
              <li>Needs practice: {summary.needs_practice ?? 0}</li>
              <li>Needs additional support: {summary.needs_support ?? 0}</li>
              <li>Active gaps: {summary.active_gaps ?? 0}</li>
              <li>Resolved gaps: {summary.resolved_gaps ?? 0}</li>
            </ul>
          </section>

          <TopicList title="Mastered Topics" items={data.mastered_topics} />
          <TopicList title="Improving Topics" items={data.improving_topics} />
          <TopicList title="Needs Practice" items={data.needs_practice} />
          <TopicList title="Needs Support" items={data.needs_support} />

          <section className="mt-8">
            <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Attention / Recommendations</h2>
            <ul className="mt-3 space-y-3">
              {(attention?.attention || []).map((a, i) => (
                <li key={`${a.code}-${a.topic_id}-${i}`} className="sys-card !max-w-none text-sm">
                  <p className="font-semibold">
                    {a.severity}: {a.title}
                  </p>
                  <p className="mt-1">{a.reason}</p>
                  <ul className="mt-2 list-disc pl-5 text-[var(--sys-gray)]">
                    {(a.evidence || []).map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                </li>
              ))}
              {(attention?.attention || []).length === 0 ? (
                <li className="text-sm text-[var(--sys-gray)]">No attention signals right now.</li>
              ) : null}
            </ul>
            <ul className="mt-4 space-y-2 text-sm">
              {(attention?.recommendations || []).map((r) => (
                <li key={`rec-${r.topic_id}`}>
                  <strong>{r.topic_name}</strong> ({r.status}) — {r.message}{" "}
                  {r.action === "START_PRACTICE" || r.action === "TAKE_REASSESSMENT" ? (
                    <Link href="/mastery/me" className="text-[var(--sys-blue)] underline">
                      Open My Learning
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Learning Trends</h2>
            <p className="text-xs text-[var(--sys-gray)]">{trends?.note}</p>
            <ul className="mt-2 max-h-64 space-y-1 overflow-y-auto text-xs">
              {(trends?.transitions || []).slice(-40).map((t, i) => (
                <li key={i}>
                  {t.at || "—"} · topic {t.topic_id} · {t.event_type}
                  {t.from_status ? ` · ${t.from_status} → ${t.to_status}` : ""}
                  {t.percentage != null ? ` · ${t.percentage}%` : ""}
                </li>
              ))}
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-lg font-semibold text-[var(--sys-blue)]">Recent Reassessments</h2>
            <p className="text-sm">
              Completed: {data.reassessment?.assignments?.filter((a) => a.status === "COMPLETED").length || 0} ·
              Mastered transitions: {data.reassessment?.mastered_count ?? 0} · Still developing (failures):{" "}
              {data.reassessment?.failed_count ?? 0}
            </p>
          </section>
        </>
      ) : null}
    </div>
  );
}

function TopicList({ title, items }) {
  if (!items?.length) return null;
  return (
    <section className="mt-6">
      <h2 className="text-lg font-semibold text-[var(--sys-blue)]">{title}</h2>
      <ul className="mt-2 space-y-2">
        {items.map((t) => (
          <li key={t.topic_id} className="sys-card !max-w-none text-sm">
            <p className="font-semibold">
              {INDICATOR[t.indicator] || "⚪"} {t.topic_name}
            </p>
            <p>
              {t.previous_status ? `${t.previous_status} → ` : ""}
              <strong>{t.status}</strong>
              {t.trend ? ` · Trend: ${t.trend.replace(/_/g, " ").toLowerCase()}` : ""}
            </p>
            {t.practice_accuracy_series?.length ? (
              <p className="text-[var(--sys-gray)]">
                Practice accuracy: {t.practice_accuracy_series.map((p) => `${p}%`).join(" → ")}
              </p>
            ) : null}
            {t.recommendation?.message ? (
              <p className="mt-1">{t.recommendation.message}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
