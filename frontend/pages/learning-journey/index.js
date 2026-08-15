import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getCourses,
  getFacultyJourneyStudent,
  getFacultyJourneyStudents,
  getMe,
  recommendFacultyJourneyAction,
} from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

export default function FacultyLearningJourneyPage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");

  const load = async (cid) => {
    const res = await getFacultyJourneyStudents(cid);
    setRows(res.data.students || []);
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        const role = (me.data.role || "").toLowerCase();
        if (role === "student") {
          setError("Faculty/admin access required. Students: /learning-journey/me");
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

  const openStudent = async (sid) => {
    setError("");
    try {
      const res = await getFacultyJourneyStudent(sid, Number(courseId));
      setSelected(res.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const recommend = async () => {
    if (!selected) return;
    setMessage("");
    try {
      await recommendFacultyJourneyAction(selected.student_id, {
        course_id: Number(courseId),
        action_type: "HUMAN_EXPERT_SUPPORT",
        topic_id: selected.current_topic?.id,
        reason: reason || "Consider human expert support. Assign a P0-014 intervention to make this official.",
      });
      setMessage("Advisory recommendation sent. Assign the real intervention from Remedial.");
      await openStudent(selected.student_id);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Faculty</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Student learning journeys</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        See each student’s current state and recommended next action. You cannot change mastery or scores here.
      </p>
      {error ? <p className="mt-3 text-red-700" role="alert">{error}</p> : null}
      {message ? <p className="mt-3 text-green-800">{message}</p> : null}

      <label className="mt-4 block text-sm" htmlFor="fac-course">
        Course
        <select
          id="fac-course"
          className="input-field ml-2"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            setSelected(null);
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

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr>
              <th className="py-2 pr-3">Student</th>
              <th className="py-2 pr-3">State</th>
              <th className="py-2 pr-3">Next action</th>
              <th className="py-2 pr-3">Reason</th>
              <th className="py-2 pr-3">Support</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.student_id} className="border-t">
                <td className="py-2 pr-3">
                  <button type="button" className="text-[var(--sys-blue)] underline" onClick={() => openStudent(s.student_id)}>
                    {s.student_name || s.student_id}
                  </button>
                </td>
                <td className="py-2 pr-3">{(s.journey_state || "").replaceAll("_", " ")}</td>
                <td className="py-2 pr-3">{s.next_action_title || "—"}</td>
                <td className="py-2 pr-3">{s.reason || "—"}</td>
                <td className="py-2 pr-3">{s.support_needed ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected ? (
        <section className="sys-card mt-6 !max-w-none" aria-labelledby="detail-heading">
          <h2 id="detail-heading" className="text-lg font-bold text-[var(--sys-blue)]">
            {selected.student_name}
          </h2>
          <p className="mt-2 text-sm">
            State: {(selected.journey_state || "").replaceAll("_", " ")}
            {selected.current_topic ? ` · Topic: ${selected.current_topic.name}` : ""}
          </p>
          <p className="mt-2 text-sm font-semibold">
            Recommended: {selected.next_best_action?.title || "None"}
          </p>
          <p className="mt-1 text-sm">{selected.next_best_action?.reason}</p>
          <p className="mt-1 text-xs text-[var(--sys-gray)]">
            Source: {selected.next_best_action?.source}. This view does not change mastery.
          </p>
          <label className="mt-4 block text-sm" htmlFor="fac-reason">
            Advisory note
            <input
              id="fac-reason"
              className="input-field mt-1 w-full"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Suggest human expert support…"
            />
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={recommend}>
              Recommend expert support
            </button>
            <Link href="/remedial" className="rounded-xl border px-4 py-2 text-sm no-underline">
              Assign via Remedial
            </Link>
            <Link href="/learning-sessions" className="rounded-xl border px-4 py-2 text-sm no-underline">
              Learning sessions
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}
