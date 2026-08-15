import { useEffect, useState } from "react";
import Link from "next/link";
import {
  chooseLearningAction,
  chooseSubjectTopic,
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
  const [subjectId, setSubjectId] = useState("");
  const [prereqChoice, setPrereqChoice] = useState(null);

  const load = async (cid, sid) => {
    const res = await getMyLearningJourney(cid, sid || undefined);
    setData(res.data);
    const selected = res.data?.subject_guidance?.selected_subject?.id;
    if (selected) setSubjectId(String(selected));
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
            setSubjectId("");
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

      {(data?.subjects || []).length ? (
        <section className="sys-card mt-6 !max-w-none" aria-labelledby="subjects-heading">
          <h2 id="subjects-heading" className="text-lg font-bold text-[var(--sys-blue)]">
            Choose a subject
          </h2>
          <p className="mt-1 text-sm text-[var(--sys-gray)]">
            You may start any enrolled subject at any time. SYS does not require a subject sequence.
          </p>
          <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Enrolled subjects">
            {(data.subjects || []).map((s) => {
              const selected = String(s.id) === String(subjectId);
              return (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  className={selected ? "btn-primary" : "rounded-xl border px-4 py-2 text-sm"}
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      setSubjectId(String(s.id));
                      await load(Number(courseId), s.id);
                    })
                  }
                >
                  {s.name}
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      {data?.subject_guidance ? (
        <section className="sys-card mt-6 !max-w-none" aria-labelledby="topic-rec-heading">
          <h2 id="topic-rec-heading" className="text-lg font-bold text-[var(--sys-blue)]">
            {data.subject_guidance.selected_subject?.name}: recommended next topic
          </h2>
          {data.subject_guidance.recommended_topic ? (
            <>
              <p className="mt-2 text-base font-semibold">
                ★ {data.subject_guidance.recommended_topic.topic_name}
              </p>
              <p className="mt-1 text-sm">{data.subject_guidance.reason}</p>
              <Link
                href={data.subject_guidance.href_start_learning || "/learning-sessions"}
                className="btn-primary mt-4 inline-flex no-underline"
              >
                Start Learning
              </Link>
            </>
          ) : (
            <p className="mt-2 text-sm text-[var(--sys-gray)]">No topics in this subject yet.</p>
          )}
          {data.subject_guidance.prerequisite_warning?.message ? (
            <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-3 py-3 text-sm">
              <p className="font-semibold">Prerequisite guidance</p>
              <p className="mt-1">{data.subject_guidance.prerequisite_warning.message}</p>
              {data.subject_guidance.prerequisite_warning.blocking ? (
                <p className="mt-1">This topic is blocked by an existing academic rule.</p>
              ) : (
                <p className="mt-1 text-[var(--sys-gray)]">Advisory only — you may continue.</p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {(data.subject_guidance.prerequisite_warning.options || []).map((opt) => (
                  <button
                    key={opt.action}
                    type="button"
                    className="rounded-xl border bg-white px-3 py-1"
                    disabled={busy}
                    onClick={async () => {
                      const def = data.subject_guidance.prerequisite_warning.deficient?.[0];
                      if (opt.action === "LEARN_PREREQUISITE" && def) {
                        await run(() =>
                          chooseSubjectTopic(Number(courseId), Number(subjectId), def.topic_id)
                        );
                        setPrereqChoice(def);
                      } else if (opt.href) {
                        window.location.href = opt.href;
                      } else {
                        setPrereqChoice({ continued: true });
                      }
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {prereqChoice?.topic_name ? (
                <p className="mt-2">Teaching target set to {prereqChoice.topic_name}.</p>
              ) : null}
              {prereqChoice?.continued ? (
                <p className="mt-2">You can continue with the selected topic.</p>
              ) : null}
            </div>
          ) : null}
          {(data.subject_guidance.topics || []).length ? (
            <div className="mt-4">
              <p className="text-sm font-semibold">Other topics in this subject</p>
              <p className="text-xs text-[var(--sys-gray)]">
                You may choose a different topic. SYS will not switch you to another subject.
              </p>
              <ul className="mt-2 space-y-2">
                {data.subject_guidance.topics
                  .filter(
                    (t) => t.topic_id !== data.subject_guidance.recommended_topic?.topic_id
                  )
                  .map((t) => (
                    <li key={t.topic_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span>
                        {t.mastered ? "✓ " : ""}
                        {t.topic_name}
                        <span className="ml-2 text-[var(--sys-gray)]">
                          {(t.mastery_status || "").replaceAll("_", " ")}
                        </span>
                      </span>
                      {!t.mastered ? (
                        <button
                          type="button"
                          className="rounded-xl border px-3 py-1"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () => chooseSubjectTopic(Number(courseId), Number(subjectId), t.topic_id),
                              `Teaching target: ${t.topic_name}`
                            )
                          }
                        >
                          Study this topic
                        </button>
                      ) : null}
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {(() => {
        const bal = data?.subject_guidance?.course_balance || data?.course_balance;
        if (!bal) return null;
        const warn = bal.status && bal.status !== "BALANCED";
        return (
          <section className="sys-card mt-6 !max-w-none" aria-labelledby="balance-heading">
            <h2 id="balance-heading" className="text-lg font-bold text-[var(--sys-blue)]">
              Course balance
            </h2>
            {warn ? (
              <p className="mt-2 text-sm font-semibold text-amber-800">
                ⚠ {bal.lagging_subject?.subject_name || "A subject"} is currently behind your other subjects.
              </p>
            ) : (
              <p className="mt-2 text-sm text-[var(--sys-gray)]">
                Subject progress differences are within a normal range. You may still choose any subject.
              </p>
            )}
            <p className="mt-2 text-sm">{bal.reason}</p>
            <ul className="mt-3 space-y-2">
              {(bal.subjects || []).map((s) => (
                <li key={s.subject_id} className="text-sm">
                  <span className="font-semibold">{s.subject_name}</span>
                  <span className="ml-2">{s.coverage_percent}%</span>
                  <span className="ml-2 text-[var(--sys-gray)]">
                    {s.mastered_topics}/{s.total_topics} mastered
                  </span>
                </li>
              ))}
            </ul>
            {warn ? (
              <p className="mt-3 text-sm">
                {bal.recommended_action ||
                  "Consider allocating additional study time to the lagging subject. This is not a command to stop another subject."}
              </p>
            ) : null}
          </section>
        );
      })()}

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
