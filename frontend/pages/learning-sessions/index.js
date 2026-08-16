import { useEffect, useState } from "react";
import Link from "next/link";
import { getApiErrorMessage, getMe, listLearningSessions } from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function LearningSessionsIndexPage() {
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [role, setRole] = useState("");

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        setRole((me.data.role || "").toLowerCase());
        const res = await listLearningSessions();
        setSessions(res.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Learning Sessions</h1>
      <p className="mt-2 text-sm text-[var(--sys-gray)]">
        Open a session in the AI digital classroom. Board-first teaching — not a chatbot.
      </p>
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
            No sessions yet{isStaffRole(role) ? " — create one via the API or faculty tools." : "."}
          </li>
        ) : null}
      </ul>
    </div>
  );
}
