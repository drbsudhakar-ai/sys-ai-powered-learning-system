import { useEffect, useState } from "react";
import Link from "next/link";
import {
  activateRemedialGroup,
  activateRemedialIntervention,
  createIndividualIntervention,
  getApiErrorMessage,
  getCourses,
  getMe,
  listRemedialGaps,
  listRemedialGroups,
  listRemedialInterventions,
  patchRemedialIntervention,
  proposeRemedialGroups,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function RemedialFacultyPage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [proposals, setProposals] = useState(null);
  const [groups, setGroups] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async (cid) => {
    if (!cid) return;
    const [g, i, gap] = await Promise.all([
      listRemedialGroups({ course_id: cid }),
      listRemedialInterventions({ course_id: cid }),
      listRemedialGaps(cid),
    ]);
    setGroups(g.data || []);
    setInterventions(i.data || []);
    setGaps(gap.data || []);
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
    try {
      await fn();
      if (courseId) await load(Number(courseId));
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Remedial Learning</h1>
      <p className="mt-1 text-sm text-[var(--sys-gray)]">
        Form explainable groups from P0-012 learning gaps and assign AI Lecturer sessions.
      </p>
      {error ? <p className="mt-3 text-red-600">{error}</p> : null}

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Course
          <select
            className="input-field ml-2"
            value={courseId}
            onChange={async (e) => {
              setCourseId(e.target.value);
              setProposals(null);
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
        <button
          type="button"
          className="btn-primary"
          disabled={!courseId || busy}
          onClick={() =>
            run(async () => {
              const res = await proposeRemedialGroups(Number(courseId), true);
              setProposals(res.data);
            })
          }
        >
          Generate proposals
        </button>
      </div>

      {proposals ? (
        <section className="sys-card mt-6 !max-w-none">
          <h2 className="font-bold text-[var(--sys-blue)]">Latest proposals</h2>
          {(proposals.common_groups || []).map((g) => (
            <div key={g.id || g.scope_name} className="mt-3 border-t pt-3 text-sm">
              <p className="font-semibold">
                COMMON · {g.scope_name} · {g.severity}
              </p>
              <p className="mt-1">{g.explanation?.summary}</p>
              <ul className="mt-1 list-disc pl-5">
                {(g.explanation?.why_grouped || []).map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              {g.id ? (
                <button
                  type="button"
                  className="btn-secondary mt-2"
                  disabled={busy}
                  onClick={() => run(() => activateRemedialGroup(g.id))}
                >
                  Activate group + session
                </button>
              ) : null}
            </div>
          ))}
          {(proposals.individual_candidates || []).map((c) => (
            <div key={c.gap?.learning_gap_id} className="mt-3 border-t pt-3 text-sm">
              <p className="font-semibold">INDIVIDUAL · {c.gap?.scope_name}</p>
              <p>{c.explanation?.summary}</p>
              <p className="mt-1 text-[var(--sys-gray)]">{c.gap?.priority_explanation}</p>
              <button
                type="button"
                className="btn-secondary mt-2"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const created = await createIndividualIntervention({
                      course_id: Number(courseId),
                      learning_gap_id: c.gap.learning_gap_id,
                    });
                    await activateRemedialIntervention(created.data.id);
                  })
                }
              >
                Create & activate individual
              </button>
            </div>
          ))}
        </section>
      ) : null}

      <section className="sys-card mt-6 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Eligible gaps ({gaps.length})</h2>
        <ul className="mt-2 space-y-1 text-sm">
          {gaps.slice(0, 20).map((g) => (
            <li key={g.learning_gap_id}>
              Student {g.student_id}: {g.scope_name} · {g.classification} · {g.severity}
            </li>
          ))}
        </ul>
      </section>

      <section className="sys-card mt-6 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Groups</h2>
        <ul className="mt-2 space-y-3 text-sm">
          {groups.map((g) => (
            <li key={g.id} className="border-t pt-3">
              <p className="font-semibold">
                #{g.id} {g.scope_name} · {g.status} · {g.severity}
              </p>
              <p>{g.explanation?.summary}</p>
              {g.learning_session_id ? (
                <Link
                  href={`/learning-sessions/${g.learning_session_id}/lecture`}
                  className="text-[var(--sys-blue)]"
                >
                  Open classroom
                </Link>
              ) : g.status === "PROPOSED" ? (
                <button
                  type="button"
                  className="btn-secondary mt-1"
                  disabled={busy}
                  onClick={() => run(() => activateRemedialGroup(g.id))}
                >
                  Activate
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="sys-card mt-6 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Interventions</h2>
        <ul className="mt-2 space-y-3 text-sm">
          {interventions.map((i) => (
            <li key={i.id} className="border-t pt-3">
              <p className="font-semibold">
                #{i.id} {i.gap_snapshot?.scope_name} · {i.mode} · {i.status} · outcome {i.outcome}
              </p>
              <p>{i.priority_explanation}</p>
              <p>
                Reassessment: {i.reassessment_required ? "required" : "no"}
                {i.reassessment_completed ? " (done)" : ""}
              </p>
              {i.status === "DRAFT" ? (
                <button
                  type="button"
                  className="btn-secondary mt-1"
                  disabled={busy}
                  onClick={() => run(() => activateRemedialIntervention(i.id))}
                >
                  Activate
                </button>
              ) : null}
              {i.status === "ASSIGNED" || i.status === "IN_PROGRESS" ? (
                <button
                  type="button"
                  className="btn-primary mt-1"
                  disabled={busy}
                  onClick={() =>
                    run(() =>
                      patchRemedialIntervention(i.id, {
                        status: i.status === "ASSIGNED" ? "IN_PROGRESS" : "COMPLETED",
                      })
                    )
                  }
                >
                  {i.status === "ASSIGNED" ? "Mark in progress" : "Complete"}
                </button>
              ) : null}
              {i.learning_session_id ? (
                <div className="mt-1">
                  <Link
                    href={`/learning-sessions/${i.learning_session_id}/lecture`}
                    className="text-[var(--sys-blue)]"
                  >
                    Classroom
                  </Link>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
