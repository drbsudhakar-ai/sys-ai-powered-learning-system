import { useEffect, useState } from "react";
import Link from "next/link";
import { getApiErrorMessage, getMe, getMyRemedial } from "../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../src/auth";

export default function MyRemedialPage() {
  const [data, setData] = useState({ interventions: [], groups: [] });
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if ((me.data.role || "").toLowerCase() !== "student") {
          setError("Student access required. Faculty: use /remedial");
          return;
        }
        const res = await getMyRemedial();
        setData(res.data || { interventions: [], groups: [] });
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
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">My Remedial Learning</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Assigned interventions based on your learning gaps. Other students&apos; scores are never shown.
      </p>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}

      <section className="sys-card mt-6 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Assignments</h2>
        {!data.interventions?.length ? (
          <p className="mt-2 text-sm">No remedial assignments yet.</p>
        ) : (
          <ul className="mt-3 space-y-4 text-sm">
            {data.interventions.map((i) => (
              <li key={i.id} className="border-t pt-3">
                <p className="font-semibold text-[var(--sys-blue)]">
                  {i.gap_snapshot?.scope_name || "Topic"} · {i.status}
                </p>
                <p className="mt-1">{i.explanation?.why_assigned}</p>
                <p className="mt-1 text-[var(--sys-gray)]">{i.explanation?.why_intervention}</p>
                <p className="mt-1">
                  Mode {i.mode} · Severity {i.gap_snapshot?.severity} · Outcome {i.outcome}
                </p>
                <p>
                  Reassessment:{" "}
                  {i.reassessment_required
                    ? i.reassessment_completed
                      ? "completed"
                      : "required"
                    : "not required"}
                </p>
                {i.learning_session_id ? (
                  <Link
                    href={`/learning-sessions/${i.learning_session_id}/lecture`}
                    className="btn-primary mt-2 inline-block no-underline"
                  >
                    Enter AI classroom
                  </Link>
                ) : (
                  <p className="mt-2 text-[var(--sys-gray)]">Session not activated yet.</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="sys-card mt-6 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Groups</h2>
        <ul className="mt-2 space-y-3 text-sm">
          {(data.groups || []).map((g) => (
            <li key={g.id} className="border-t pt-3">
              <p className="font-semibold">{g.scope_name} · {g.status}</p>
              <p>{g.student_friendly_reason || g.explanation?.summary}</p>
              {g.learning_session_id ? (
                <Link
                  href={`/learning-sessions/${g.learning_session_id}/lecture`}
                  className="text-[var(--sys-blue)]"
                >
                  Open session
                </Link>
              ) : null}
            </li>
          ))}
          {!data.groups?.length ? <li className="text-sm">No group memberships.</li> : null}
        </ul>
      </section>
    </div>
  );
}
