import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { createLearningSession, getApiErrorMessage, getMe, listLearningSessions } from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function LearningSessionsIndexPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [role, setRole] = useState("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", mode: "COMMON", primary_student_id: "" });

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        setRole((me.data.role || "").toLowerCase());
        const res = await listLearningSessions({
          course_id: router.query.course_id || undefined,
          subject_id: router.query.subject_id || undefined,
          topic_id: router.query.topic_id || undefined,
        });
        setSessions(res.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, router.query.course_id, router.query.subject_id, router.query.topic_id]);

  const create = async (event) => {
    event.preventDefault();
    setCreating(true);
    setError("");
    try {
      const payload = {
        title: form.title,
        mode: form.mode,
        course_id: Number(router.query.course_id),
        subject_id: router.query.subject_id ? Number(router.query.subject_id) : null,
        topic_id: router.query.topic_id ? Number(router.query.topic_id) : null,
        primary_student_id: form.mode === "INDIVIDUAL" ? Number(form.primary_student_id) : null,
      };
      const { data } = await createLearningSession(payload);
      await router.push(`/learning-sessions/${data.id}/lecture?course_id=${payload.course_id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "The learning session could not be created."));
      setCreating(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Learning Sessions</h1>
      <p className="mt-2 text-sm text-[var(--sys-gray)]">
        Open a session in the AI digital classroom. Board-first teaching — not a chatbot.
      </p>
      <p className="mt-2"><Link href={router.query.course_id ? `/courses/${router.query.course_id}/workspace` : "/courses"}>Choose a course and syllabus topic</Link> to {isStaffRole(role) ? "prepare a faculty-led classroom" : "start individual learning"}.</p>
      {isStaffRole(role) && router.query.course_id && router.query.topic_id ? (
        <form className="sys-card !max-w-none mt-6" onSubmit={create}>
          <p className="font-semibold text-[var(--sys-blue)]">Plan a syllabus learning session</p>
          <p className="mt-1 text-sm text-[var(--sys-gray)]">Common teaches a shared class; Hybrid keeps shared teaching with individual evidence; Individual requires one enrolled student.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <input aria-label="Session title" required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Session title" />
            <select aria-label="Learning mode" value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
              <option value="COMMON">Common classroom</option>
              <option value="HYBRID">Hybrid classroom</option>
              <option value="INDIVIDUAL">Individual learning</option>
            </select>
            {form.mode === "INDIVIDUAL" ? <input required type="number" min="1" value={form.primary_student_id} onChange={(event) => setForm({ ...form, primary_student_id: event.target.value })} placeholder="Enrolled student ID" /> : null}
          </div>
          <button type="submit" className="btn-primary mt-4" disabled={creating}>{creating ? "Preparing classroom…" : "Create learning session"}</button>
        </form>
      ) : null}
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      <ul className="mt-6 space-y-3">
        {sessions.map((s) => (
          <li key={s.id} className="sys-card !max-w-none">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold text-[var(--sys-blue)]">{s.title}</p>
                <p className="text-sm">
                  {s.mode} · {s.status}
                </p>
              </div>
              <Link
                href={`/learning-sessions/${s.id}/lecture`}
                className="btn-primary no-underline inline-block"
              >
                Enter classroom
              </Link>
            </div>
          </li>
        ))}
        {!sessions.length && !error ? (
          <li className="text-sm text-[var(--sys-gray)]">
            No sessions yet{isStaffRole(role) ? " — choose a course topic above, then prepare a classroom." : " — start an individual lesson from My Courses, or ask your faculty member for a common-session invitation."}
          </li>
        ) : null}
      </ul>
    </div>
  );
}
