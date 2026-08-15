import { useEffect, useState } from "react";
import Link from "next/link";
import {
  adminListStudents,
  approveReassessment,
  getApiErrorMessage,
  getCourses,
  getMe,
  getStudentMastery,
  getTopicMastery,
  updateMasteryPolicy,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

const INDICATOR = {
  GREEN: "🟢",
  YELLOW: "🟡",
  ORANGE: "🟠",
  RED: "🔴",
  GRAY: "⚪",
};

export default function MasteryFacultyPage() {
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [data, setData] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [threshold, setThreshold] = useState(80);

  const load = async (sid, cid) => {
    const res = await getStudentMastery(sid, cid, true);
    setData(res.data);
    setThreshold(res.data?.policy?.mastery_threshold ?? 80);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Faculty/admin access required.");
          return;
        }
        const [crs, stu] = await Promise.all([
          getCourses(),
          adminListStudents().catch(() => ({ data: [] })),
        ]);
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

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Mastery Overview</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Indicators come from backend mastery policy — not frontend scoring.
      </p>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}

      <div className="mt-4 flex flex-wrap gap-3">
        <select className="input-field" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
          <option value="">Course…</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
        <select className="input-field" value={studentId} onChange={(e) => setStudentId(e.target.value)}>
          <option value="">Student…</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name || s.email} ({s.id})
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn-primary"
          disabled={!courseId || !studentId}
          onClick={async () => {
            try {
              setError("");
              await load(Number(studentId), Number(courseId));
            } catch (err) {
              setError(getApiErrorMessage(err));
            }
          }}
        >
          Load mastery
        </button>
      </div>

      {data ? (
        <section className="sys-card mt-6 !max-w-none">
          <h2 className="font-bold text-[var(--sys-blue)]">Policy</h2>
          <div className="mt-2 flex flex-wrap items-end gap-2 text-sm">
            <label>
              Mastery threshold %
              <input
                className="input-field ml-2 w-24"
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
            </label>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                try {
                  await updateMasteryPolicy({
                    course_id: Number(courseId),
                    mastery_threshold: threshold,
                  });
                  await load(Number(studentId), Number(courseId));
                } catch (err) {
                  setError(getApiErrorMessage(err));
                }
              }}
            >
              Save threshold
            </button>
          </div>
        </section>
      ) : null}

      <ul className="mt-6 space-y-3">
        {(data?.topics || []).map((t) => (
          <li key={t.topic_id} className="sys-card !max-w-none text-sm">
            <p className="font-semibold">
              {INDICATOR[t.indicator] || "⚪"} {t.topic_name} · {t.status}
              {t.mastery_percent != null ? ` · ${t.mastery_percent}%` : ""}
            </p>
            <p className="text-[var(--sys-gray)]">{t.explanation?.summary}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  try {
                    const res = await getTopicMastery(Number(studentId), Number(courseId), t.topic_id);
                    setDetail(res.data);
                  } catch (err) {
                    setError(getApiErrorMessage(err));
                  }
                }}
              >
                Evidence / history
              </button>
              {t.status !== "MASTERED" ? (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={async () => {
                    try {
                      await approveReassessment({
                        course_id: Number(courseId),
                        topic_id: t.topic_id,
                        student_id: Number(studentId),
                      });
                      await load(Number(studentId), Number(courseId));
                    } catch (err) {
                      setError(getApiErrorMessage(err));
                    }
                  }}
                >
                  Approve reassessment
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>

      {detail ? (
        <section className="sys-card mt-6 !max-w-none text-sm">
          <h2 className="font-bold text-[var(--sys-blue)]">
            History — {detail.topic_name || detail.topic_id}
          </h2>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">
            {JSON.stringify(detail.explanation, null, 2)}
          </pre>
          <ul className="mt-3 space-y-2">
            {(detail.history || []).map((h) => (
              <li key={h.id} className="border-t pt-2">
                <strong>{h.event_type}</strong> {h.from_status} → {h.to_status}
                <div className="text-[var(--sys-gray)]">{h.explanation?.summary}</div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="mt-6 text-sm">
        <Link href="/performance" className="text-[var(--sys-blue)]">
          Performance
        </Link>
        {" · "}
        <Link href="/remedial" className="text-[var(--sys-blue)]">
          Remedial
        </Link>
      </p>
    </div>
  );
}
