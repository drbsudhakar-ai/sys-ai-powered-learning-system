import { useEffect, useState } from "react";
import {
  getAdminJourneyOverview,
  getApiErrorMessage,
  getCourses,
  getMe,
} from "../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../src/auth";

export default function AdminLearningJourneyPage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = async (cid) => {
    const res = await getAdminJourneyOverview(cid ? { course_id: cid } : {});
    setData(res.data);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isAdminRole(me.data.role)) {
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

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Admin</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Learning journey overview</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Aggregate orchestration demand only — individual student journeys are not listed here.
      </p>
      {error ? <p className="mt-3 text-red-700" role="alert">{error}</p> : null}

      <label className="mt-4 block text-sm" htmlFor="admin-course">
        Course filter
        <select
          id="admin-course"
          className="input-field ml-2"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            await load(e.target.value);
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

      {data ? (
        <ul className="mt-6 grid gap-3 sm:grid-cols-2">
          <li className="sys-card !max-w-none">Waiting for support: {data.students_waiting_for_support}</li>
          <li className="sys-card !max-w-none">Remedial demand: {data.remedial_learning_demand}</li>
          <li className="sys-card !max-w-none">Unresolved journeys: {data.unresolved_learning_journeys}</li>
          <li className="sys-card !max-w-none">Mastered topic states: {data.mastered_topic_states}</li>
        </ul>
      ) : null}

      {(data?.topic_bottlenecks || []).length ? (
        <section className="sys-card mt-6 !max-w-none">
          <h2 className="text-lg font-bold text-[var(--sys-blue)]">Topic bottlenecks</h2>
          <ul className="mt-3 space-y-1 text-sm">
            {data.topic_bottlenecks.map((b) => (
              <li key={`${b.course_id}-${b.topic_id}`}>
                {b.topic_name || `Topic ${b.topic_id}`}: {b.open_support_actions} open support actions
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
