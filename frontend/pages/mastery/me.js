import { useEffect, useState } from "react";
import Link from "next/link";
import {
  declareReassessmentReady,
  getApiErrorMessage,
  getCourses,
  getMe,
  getMyMastery,
  getReassessmentEligibility,
  recommendPractice,
  startPractice,
  startReassessment,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

const INDICATOR = {
  GREEN: "🟢",
  YELLOW: "🟡",
  ORANGE: "🟠",
  RED: "🔴",
  GRAY: "⚪",
};

export default function MyMasteryPage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = async (cid) => {
    const res = await getMyMastery(cid);
    setData(res.data);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if ((me.data.role || "").toLowerCase() !== "student") {
          setError("Student access required. Faculty: use /mastery");
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

  const run = async (fn) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const out = await fn();
      if (courseId) await load(Number(courseId));
      return out;
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">My Learning</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Practice and reassessment drive mastery. Completing a remedial lecture alone does not mark mastery.
      </p>
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

      {data?.policy ? (
        <p className="mt-3 text-xs text-[var(--sys-gray)]">
          Thresholds — mastery {data.policy.mastery_threshold}% · practice {data.policy.practice_threshold}% ·
          reassessment {data.policy.reassessment_threshold}%
        </p>
      ) : null}

      <ul className="mt-6 space-y-4">
        {(data?.topics || []).map((t) => (
          <li key={t.topic_id} className="sys-card !max-w-none">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-lg font-semibold text-[var(--sys-blue)]">
                  {INDICATOR[t.indicator] || "⚪"} {t.topic_name || `Topic ${t.topic_id}`}
                </p>
                <p className="text-sm">
                  Status: <strong>{t.status}</strong>
                  {t.mastery_percent != null ? ` · ${t.mastery_percent}%` : ""}
                  {t.practice_accuracy != null ? ` · practice ${t.practice_accuracy}%` : ""}
                </p>
                <p className="mt-1 text-sm text-[var(--sys-gray)]">
                  {t.explanation?.summary || "No decision yet."}
                </p>
                {t.remediation_source ? (
                  <p className="text-xs">Learning path noted: {t.remediation_source} (does not decide mastery)</p>
                ) : null}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const r = await recommendPractice({
                      course_id: Number(courseId),
                      topic_id: t.topic_id,
                    });
                    setMessage((r.data.why_selected || []).join(" · "));
                  })
                }
              >
                Why practice?
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const r = await startPractice({
                      course_id: Number(courseId),
                      topic_id: t.topic_id,
                    });
                    window.location.href = r.data.start_path;
                  })
                }
              >
                Start practice
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await declareReassessmentReady({
                      course_id: Number(courseId),
                      topic_id: t.topic_id,
                      remediation_source: "SELF_STUDY",
                    });
                    const e = await getReassessmentEligibility({
                      course_id: Number(courseId),
                      topic_id: t.topic_id,
                    });
                    setMessage(
                      e.data.eligible
                        ? `Ready: ${(e.data.reasons || []).join("; ")}`
                        : `Not ready: ${(e.data.reasons || []).join("; ")}`
                    );
                  })
                }
              >
                I studied (self-study)
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy || t.status === "MASTERED"}
                onClick={() =>
                  run(async () => {
                    const r = await startReassessment({
                      course_id: Number(courseId),
                      topic_id: t.topic_id,
                    });
                    window.location.href = r.data.start_path;
                  })
                }
              >
                Start reassessment
              </button>
            </div>
          </li>
        ))}
        {courseId && !data?.topics?.length ? (
          <li className="text-sm text-[var(--sys-gray)]">No topic mastery rows yet — take an assessment first.</li>
        ) : null}
      </ul>

      <p className="mt-6 text-sm">
        <Link href="/remedial/me" className="text-[var(--sys-blue)]">
          Remediat assignments
        </Link>
        {" · "}
        <Link href="/student/assessments" className="text-[var(--sys-blue)]">
          My assessments
        </Link>
      </p>
    </div>
  );
}
