import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminListSubjects,
  archiveAssessment,
  assembleAssessment,
  createQuestion,
  createTopic,
  getApiErrorMessage,
  getAssessment,
  getMe,
  listTopics,
  publishAssessment,
  setAssessmentBlueprint,
} from "../../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../../src/auth";

const DIFFS = ["EASY", "MEDIUM", "HARD", "ADVANCED"];

export default function EditAssessmentPage() {
  const router = useRouter();
  const { id } = router.query;
  const [assessment, setAssessment] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [seedMsg, setSeedMsg] = useState("");

  const refresh = async () => {
    const [a, s] = await Promise.all([getAssessment(id), adminListSubjects()]);
    setAssessment(a.data);
    setSubjects(s.data || []);
    setRows(
      (a.data.blueprint_items || []).map((i) => ({
        subject_id: String(i.subject_id),
        topic_id: i.topic_id ? String(i.topic_id) : "",
        difficulty: i.difficulty,
        question_count: i.question_count,
      }))
    );
    if (!rows.length && !(a.data.blueprint_items || []).length) {
      setRows([{ subject_id: "", topic_id: "", difficulty: "MEDIUM", question_count: 1 }]);
    }
  };

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Staff access required.");
          setLoading(false);
          return;
        }
        await refresh();
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router.isReady, id]);

  useEffect(() => {
    const subjectIds = [...new Set(rows.map((r) => r.subject_id).filter(Boolean))];
    if (!subjectIds.length) return;
    Promise.all(subjectIds.map((sid) => listTopics({ subject_id: sid })))
      .then((results) => {
        const all = results.flatMap((r) => r.data || []);
        setTopics(all);
      })
      .catch(() => {});
  }, [rows]);

  const courseSubjects = subjects.filter(
    (s) => !assessment?.course_id || !s.course_id || s.course_id === assessment.course_id
  );

  const saveBlueprint = async () => {
    setError("");
    setSuccess("");
    try {
      const items = rows
        .filter((r) => r.subject_id && r.question_count > 0)
        .map((r) => ({
          subject_id: Number(r.subject_id),
          topic_id: r.topic_id ? Number(r.topic_id) : null,
          difficulty: r.difficulty,
          question_count: Number(r.question_count),
        }));
      const res = await setAssessmentBlueprint(id, items);
      setAssessment(res.data);
      setSuccess("Blueprint saved.");
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const assemble = async () => {
    setError("");
    setSuccess("");
    try {
      const res = await assembleAssessment(id);
      if (!res.data.ok) {
        setError((res.data.errors || []).join(" ") || "Assembly failed.");
        return;
      }
      setSuccess(`Assembly OK — ${res.data.count} questions selected.`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const publish = async () => {
    setError("");
    setSuccess("");
    try {
      const res = await publishAssessment(id);
      setSuccess(`Published version v${res.data.version_number} with ${res.data.question_count} questions.`);
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const seedQuestions = async () => {
    setSeedMsg("");
    setError("");
    try {
      for (const row of rows) {
        if (!row.subject_id) continue;
        let topicId = row.topic_id ? Number(row.topic_id) : null;
        if (!topicId && assessment?.topic_id) topicId = assessment.topic_id;
        if (!topicId) {
          const t = await createTopic({
            name: `Auto Topic ${row.difficulty}`,
            subject_id: Number(row.subject_id),
          });
          topicId = t.data.id;
          row.topic_id = String(topicId);
        }
        const need = Number(row.question_count) || 1;
        for (let i = 0; i < need; i += 1) {
          await createQuestion({
            stem: `${assessment.title} Q-${row.difficulty}-${i + 1}`,
            difficulty: row.difficulty,
            course_id: assessment.course_id,
            subject_id: Number(row.subject_id),
            topic_id: topicId,
            status: "ACTIVE",
          });
        }
      }
      setSeedMsg("Seeded eligible questions for blueprint rows.");
      setRows([...rows]);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <Link href={`/assessments/${id || ""}`} className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back
      </Link>
      {loading && <p className="sys-card mt-6">Loading…</p>}
      {!loading && error && <p className="sys-card mt-6 text-red-600" role="alert">{error}</p>}
      {!loading && assessment && (
        <>
          <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Design: {assessment.title}</h1>
          <p className="text-sm text-[var(--sys-gray)]">
            {assessment.assessment_type} · {assessment.category} · {assessment.status}
          </p>
          {success && <p className="mt-2 text-sm text-green-700" role="status">{success}</p>}
          {seedMsg && <p className="mt-2 text-sm text-green-700">{seedMsg}</p>}

          <section className="sys-card mt-6 !max-w-none">
            <h2 className="text-lg font-bold text-[var(--sys-blue)]">Blueprint</h2>
            <p className="mt-1 text-sm text-[var(--sys-gray)]">
              Configure subject / topic / difficulty question counts. Total should equal {assessment.total_questions}.
            </p>
            <div className="mt-4 space-y-3">
              {rows.map((row, idx) => (
                <div key={idx} className="grid gap-2 sm:grid-cols-5">
                  <select
                    className="input-field"
                    aria-label={`Subject row ${idx + 1}`}
                    value={row.subject_id}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...next[idx], subject_id: e.target.value, topic_id: "" };
                      setRows(next);
                    }}
                  >
                    <option value="">Subject…</option>
                    {courseSubjects.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <select
                    className="input-field"
                    aria-label={`Topic row ${idx + 1}`}
                    value={row.topic_id}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...next[idx], topic_id: e.target.value };
                      setRows(next);
                    }}
                  >
                    <option value="">Topic (optional)…</option>
                    {topics
                      .filter((t) => String(t.subject_id) === String(row.subject_id))
                      .map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                  </select>
                  <select
                    className="input-field"
                    aria-label={`Difficulty row ${idx + 1}`}
                    value={row.difficulty}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...next[idx], difficulty: e.target.value };
                      setRows(next);
                    }}
                  >
                    {DIFFS.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min={1}
                    className="input-field"
                    aria-label={`Count row ${idx + 1}`}
                    value={row.question_count}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...next[idx], question_count: e.target.value };
                      setRows(next);
                    }}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setRows(rows.filter((_, i) => i !== idx))}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() =>
                  setRows([...rows, { subject_id: "", topic_id: "", difficulty: "MEDIUM", question_count: 1 }])
                }
              >
                Add row
              </button>
              <button type="button" className="btn-primary" onClick={saveBlueprint}>Save Blueprint</button>
              <button type="button" className="btn-secondary" onClick={seedQuestions}>Seed Questions</button>
              <button type="button" className="btn-secondary" onClick={assemble}>Assemble Preview</button>
              <button type="button" className="btn-primary" onClick={publish}>Publish</button>
              <button
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  await archiveAssessment(id);
                  router.push("/assessments");
                }}
              >
                Archive
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
