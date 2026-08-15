import { useEffect, useState } from "react";
import Link from "next/link";
import {
  chooseLearningAction,
  completeLearningAction,
  dismissLearningAction,
  getApiErrorMessage,
  getCourses,
  getMe,
  getMyLearningJourney,
  startLearningAction,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

const MARKER_LABEL = {
  mastered: "Mastered",
  learning: "Learning",
  current: "Current focus",
  needs_support: "Needs support",
  upcoming: "Upcoming",
};

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function StudentLearningJourneyPage() {
  const [me, setMe] = useState(null);
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = async (cid) => {
    const res = await getMyLearningJourney(cid);
    setData(res.data);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const user = await getMe();
        setMe(user.data);
        if ((user.data.role || "").toLowerCase() !== "student") {
          setError("Student access required. Faculty: use Journeys.");
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

  const run = async (fn, okMsg) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const out = await fn();
      if (courseId) await load(Number(courseId));
      if (okMsg) setMessage(okMsg);
      return out;
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const nba = data?.next_best_action;
  const expl = nba?.explanation || {};
  const progress = data?.progress || {};
  const resume = data?.resume;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Student</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">
        {greeting()}
        {me?.name ? `, ${me.name.split(" ")[0]}` : ""}
      </h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Here is what to focus on next. Recommendations come from your current learning state — not a hidden score.
      </p>
      {error ? <p className="mt-3 text-red-700" role="alert">{error}</p> : null}
      {message ? <p className="mt-3 text-green-800">{message}</p> : null}

      <label className="mt-4 block text-sm" htmlFor="journey-course">
        Course
        <select
          id="journey-course"
          className="input-field ml-2"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            if (e.target.value) await load(Number(e.target.value));
          }}
        >
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
      </label>

      {resume ? (
        <section className="sys-card mt-6 !max-w-none" aria-labelledby="resume-heading">
          <h2 id="resume-heading" className="text-lg font-bold text-[var(--sys-blue)]">
            Welcome back
          </h2>
          <p className="mt-2 text-sm">
            You were studying {resume.title || "a lesson"}. Last activity: AI Lecturer
            {resume.current_step_index != null
              ? ` — Step ${resume.current_step_index + 1}${resume.step_count ? ` of ${resume.step_count}` : ""}`
              : ""}
            .
          </p>
          <Link
            href={`/learning-sessions/${resume.session_id}/lecture`}
            className="btn-primary mt-4 inline-flex no-underline"
          >
            Continue learning
          </Link>
        </section>
      ) : null}

      <section className="sys-card mt-6 !max-w-none" aria-labelledby="nba-heading">
        <h2 id="nba-heading" className="text-lg font-bold text-[var(--sys-blue)]">
          Your next best step
        </h2>
        {nba ? (
          <>
            <p className="mt-2 text-base font-semibold">{nba.title}</p>
            <p className="mt-1 text-sm">
              <span className="font-semibold">Required: </span>
              {nba.mandatory ? "Yes — this academic activity is required." : "No — recommended, not forced."}
            </p>
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className="font-semibold">What</dt>
                <dd>{expl.what || nba.title}</dd>
              </div>
              <div>
                <dt className="font-semibold">Why</dt>
                <dd>{expl.why || nba.reason}</dd>
              </div>
              <div>
                <dt className="font-semibold">Source</dt>
                <dd>{expl.source || nba.source}</dd>
              </div>
              <div>
                <dt className="font-semibold">After completion</dt>
                <dd>{expl.outcome}</dd>
              </div>
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={async () => {
                  const out = await run(() => startLearningAction(nba.action_id));
                  const href = out?.data?.href || out?.data?.launch?.start_path || nba.href;
                  if (href && typeof window !== "undefined") window.location.href = href;
                }}
              >
                Start
              </button>
              <button
                type="button"
                className="rounded-xl border px-4 py-2 text-sm"
                disabled={busy}
                onClick={() => run(() => completeLearningAction(nba.action_id), "Marked complete in your journey.")}
              >
                I finished this
              </button>
              {!nba.mandatory ? (
                <button
                  type="button"
                  className="rounded-xl border px-4 py-2 text-sm"
                  disabled={busy}
                  onClick={() => run(() => dismissLearningAction(nba.action_id), "Recommendation dismissed.")}
                >
                  Not now
                </button>
              ) : null}
            </div>
          </>
        ) : (
          <p className="mt-2 text-sm text-[var(--sys-gray)]">No next step yet. Enroll in a course to begin.</p>
        )}
      </section>

      {data?.alternatives?.length ? (
        <section className="sys-card mt-6 !max-w-none" aria-labelledby="alts-heading">
          <h2 id="alts-heading" className="text-lg font-bold text-[var(--sys-blue)]">
            Other available options
          </h2>
          <p className="mt-1 text-sm text-[var(--sys-gray)]">
            You can choose how to learn. Required activities still remain required.
          </p>
          <ul className="mt-3 space-y-2">
            {data.alternatives.map((a) => (
              <li key={a.action_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span>
                  {a.title}
                  <span className="ml-2 text-[var(--sys-gray)]">({a.action_type.replaceAll("_", " ")})</span>
                </span>
                <button
                  type="button"
                  className="rounded-xl border px-3 py-1"
                  disabled={busy || !nba}
                  onClick={() =>
                    run(
                      () => chooseLearningAction(nba.action_id, { choice_action_id: a.action_id }),
                      "We’ll use this option next."
                    )
                  }
                >
                  Choose this
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="sys-card mt-6 !max-w-none" aria-labelledby="path-heading">
        <h2 id="path-heading" className="text-lg font-bold text-[var(--sys-blue)]">
          Your learning journey
        </h2>
        <p className="mt-1 text-sm text-[var(--sys-gray)]">
          Status: {data?.journey_state || "—"}
          {data?.current_topic ? ` · Current topic: ${data.current_topic.name}` : ""}
        </p>
        <ol className="mt-4 space-y-2">
          {(data?.journey || []).map((t) => (
            <li key={t.topic_id} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 font-mono" aria-hidden="true">
                {t.marker === "mastered"
                  ? "✓"
                  : t.marker === "needs_support"
                    ? "!"
                    : t.marker === "current" || t.marker === "learning"
                      ? "→"
                      : "○"}
              </span>
              <div>
                <p className="font-semibold">{t.topic_name}</p>
                <p className="text-[var(--sys-gray)]">
                  {MARKER_LABEL[t.marker] || t.marker}
                  {t.mastery_status ? ` · ${t.mastery_status.replaceAll("_", " ")}` : ""}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="sys-card mt-6 !max-w-none" aria-labelledby="plan-heading">
        <h2 id="plan-heading" className="text-lg font-bold text-[var(--sys-blue)]">
          Today’s plan
        </h2>
        {(data?.daily_plan || []).length ? (
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
            {data.daily_plan.map((p) => (
              <li key={`${p.order}-${p.action_type}`}>
                <span className="font-semibold">{p.title}</span>
                <span className="text-[var(--sys-gray)]"> — {p.when}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-2 text-sm text-[var(--sys-gray)]">A plan will appear when there are recommended actions.</p>
        )}
      </section>

      <section className="sys-card mt-6 !max-w-none" aria-labelledby="prog-heading">
        <h2 id="prog-heading" className="text-lg font-bold text-[var(--sys-blue)]">
          Progress
        </h2>
        <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3 text-sm">
          <li className="rounded-xl border px-3 py-2">Mastered: {progress.mastered ?? 0}</li>
          <li className="rounded-xl border px-3 py-2">Improving: {progress.improving ?? 0}</li>
          <li className="rounded-xl border px-3 py-2">Needs support: {progress.needs_support ?? 0}</li>
        </ul>
      </section>

      <section className="sys-card mt-6 !max-w-none" aria-labelledby="recent-heading">
        <h2 id="recent-heading" className="text-lg font-bold text-[var(--sys-blue)]">
          Recent activity
        </h2>
        {(data?.recent_activity || []).length ? (
          <ul className="mt-3 space-y-1 text-sm">
            {data.recent_activity.map((e, i) => (
              <li key={`${e.event_type}-${i}`}>
                {e.event_type.replaceAll("_", " ")}
                {e.to_status ? ` → ${e.to_status.replaceAll("_", " ")}` : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-[var(--sys-gray)]">No recent mastery events yet.</p>
        )}
      </section>
    </div>
  );
}
