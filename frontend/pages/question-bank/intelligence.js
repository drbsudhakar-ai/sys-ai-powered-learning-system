import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getCourses,
  getCourseTopicIntelligence,
  getMe,
  getTopicIntelligence,
  runHistoricalAnalysis,
  selectQuestions,
  setSubjectWeightages,
  adminListSubjects,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function IntelligenceDashboardPage() {
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [topics, setTopics] = useState([]);
  const [topicDetail, setTopicDetail] = useState(null);
  const [selection, setSelection] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Staff access required.");
          return;
        }
        const [crs, subs] = await Promise.all([getCourses(), adminListSubjects()]);
        setCourses(crs.data || []);
        setSubjects(subs.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const loadTopics = async () => {
    setError("");
    try {
      const res = await getCourseTopicIntelligence(courseId);
      setTopics(res.data || []);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const analyze = async () => {
    setError("");
    setMessage("");
    try {
      await runHistoricalAnalysis(courseId);
      setMessage("Historical analysis refreshed. Topic priorities updated.");
      await loadTopics();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const equalSubjectWeights = async () => {
    const courseSubs = subjects.filter((s) => !s.course_id || String(s.course_id) === String(courseId));
    if (!courseSubs.length) {
      setError("No subjects for course.");
      return;
    }
    const each = Math.round((100 / courseSubs.length) * 100) / 100;
    const items = courseSubs.map((s, i) => ({
      subject_id: s.id,
      weight_percent: i === courseSubs.length - 1 ? 100 - each * (courseSubs.length - 1) : each,
    }));
    await setSubjectWeightages({ course_id: Number(courseId), items });
    setMessage("Subject weightages set equally.");
  };

  const previewGrand = async () => {
    setError("");
    setSelection(null);
    const courseSubs = subjects.filter((s) => !s.course_id || String(s.course_id) === String(courseId));
    if (!courseSubs.length) {
      setError("Need subjects linked to course.");
      return;
    }
    const n = 6;
    const per = Math.floor(n / courseSubs.length) || 1;
    const subject_distribution = {};
    courseSubs.forEach((s, i) => {
      subject_distribution[s.id] = i === 0 ? n - per * (courseSubs.length - 1) : per;
    });
    try {
      const res = await selectQuestions({
        course_id: Number(courseId),
        total_questions: n,
        subject_distribution,
        difficulty_distribution: { MEDIUM: n },
        reuse_policy: "MIXED",
        evidence_based: true,
      });
      setSelection(res.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <Link href="/question-bank" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">← Question Bank</Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Topic Intelligence & Selection</h1>
      <p className="mt-2 text-sm text-[var(--sys-gray)]">
        Evidence-based priorities from historical papers. Not a prediction of exact future exam questions.
      </p>

      <div className="sys-card mt-6 !max-w-none flex flex-wrap gap-3 items-end">
        <div>
          <label htmlFor="courseId" className="mb-1 block text-sm font-semibold">Course</label>
          <select id="courseId" className="input-field" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">Select…</option>
            {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </div>
        <button type="button" className="btn-secondary" disabled={!courseId} onClick={loadTopics}>Load Topics</button>
        <button type="button" className="btn-primary" disabled={!courseId} onClick={analyze}>Run Historical Analysis</button>
        <button type="button" className="btn-secondary" disabled={!courseId} onClick={equalSubjectWeights}>Set Equal Subject Weights</button>
        <button type="button" className="btn-primary" disabled={!courseId} onClick={previewGrand}>Preview Grand Selection</button>
      </div>

      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}
      {message && <p className="sys-card mt-4 text-green-700">{message}</p>}

      {topics.length > 0 && (
        <div className="sys-card mt-4 !max-w-none overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Topic</th>
                <th>Priority</th>
                <th>Frequency</th>
                <th>Weightage %</th>
                <th>Trend</th>
                <th>Questions</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {topics.map((t) => (
                <tr key={t.topic_id} className="border-b">
                  <td>{t.topic_name}</td>
                  <td>{t.priority} ({t.priority_score})</td>
                  <td>{t.historical_frequency}</td>
                  <td>{t.weightage}</td>
                  <td>{t.trend}</td>
                  <td>{t.question_count}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-secondary !px-2 !py-1 text-xs"
                      onClick={async () => {
                        const res = await getTopicIntelligence(t.topic_id);
                        setTopicDetail(res.data);
                      }}
                    >
                      AI Lecturer view
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {topicDetail && (
        <section className="sys-card mt-4 !max-w-none">
          <h2 className="font-bold text-[var(--sys-blue)]">{topicDetail.topic?.name}</h2>
          <p className="text-sm">Priority: {topicDetail.priority} · Trend: {topicDetail.recent_trend}</p>
          <p className="mt-2 text-xs text-[var(--sys-gray)]">{topicDetail.disclaimer}</p>
          <pre className="mt-3 overflow-x-auto text-xs">{JSON.stringify({
            concepts: topicDetail.frequently_tested_concepts,
            patterns: topicDetail.important_question_patterns,
            shortcuts: topicDetail.shortcuts,
            traps: topicDetail.common_traps,
          }, null, 2)}</pre>
        </section>
      )}

      {selection && (
        <section className="sys-card mt-4 !max-w-none">
          <h2 className="font-bold text-[var(--sys-blue)]">Grand/Final Candidate Selection</h2>
          <p className="text-xs text-[var(--sys-gray)]">{selection.disclaimer}</p>
          <p className="mt-2 text-sm">Pool: {selection.pool_size} · Selected: {(selection.selected || []).length}</p>
          {(selection.errors || []).length > 0 && (
            <p className="text-sm text-red-600">{selection.errors.join(" ")}</p>
          )}
          <ul className="mt-2 list-disc pl-5 text-sm">
            {(selection.selected || []).map((s) => (
              <li key={s.question_id}>
                Q{s.question_id} · importance {s.importance_score} · {s.difficulty} · {s.evidence_label}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
