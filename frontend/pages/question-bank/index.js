import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  archiveQuestionBankItem,
  getApiErrorMessage,
  getCourses,
  getMe,
  getQuestionBankStats,
  searchQuestionBank,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function QuestionBankPage() {
  const router = useRouter();
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [q, setQ] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Staff access required.");
          return;
        }
        const crs = await getCourses();
        setCourses(crs.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, []);

  const load = async () => {
    if (!courseId) return;
    setLoading(true);
    setError("");
    try {
      const params = { course_id: courseId };
      if (q) params.q = q;
      if (difficulty) params.difficulty = difficulty;
      if (status) params.status = status;
      const [res, st] = await Promise.all([
        searchQuestionBank(params),
        getQuestionBankStats({ course_id: courseId }),
      ]);
      setItems(res.data || []);
      setStats(st.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (courseId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="sys-tagline !text-left !text-base">Question Intelligence</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Question Bank</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/question-bank/new" className="btn-primary no-underline">Create Question</Link>
          <Link href="/question-bank/intelligence" className="btn-secondary no-underline">Intelligence</Link>
          <Link href="/question-bank/historical" className="btn-secondary no-underline">Historical Papers</Link>
        </div>
      </div>

      <div className="sys-card mb-4 !max-w-none grid gap-3 sm:grid-cols-4">
        <div>
          <label htmlFor="courseId" className="mb-1 block text-sm font-semibold">Course</label>
          <select id="courseId" className="input-field" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">Select…</option>
            {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="q" className="mb-1 block text-sm font-semibold">Search</label>
          <input id="q" className="input-field" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div>
          <label htmlFor="difficulty" className="mb-1 block text-sm font-semibold">Difficulty</label>
          <select id="difficulty" className="input-field" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="">All</option>
            {["EASY", "MEDIUM", "HARD", "ADVANCED"].map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button type="button" className="btn-primary" onClick={load} disabled={!courseId}>Filter</button>
        </div>
      </div>

      {stats && (
        <p className="mb-4 text-sm text-[var(--sys-gray)]">
          Total: {stats.total} · By difficulty: {JSON.stringify(stats.by_difficulty)} · By status: {JSON.stringify(stats.by_status)}
        </p>
      )}
      {error && <p className="sys-card text-red-600" role="alert">{error}</p>}
      {loading && <p className="sys-card">Loading…</p>}
      {!loading && courseId && items.length === 0 && <p className="sys-card">No questions found.</p>}
      {!loading && items.length > 0 && (
        <div className="sys-card !max-w-none overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Question</th>
                <th>Type</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b">
                  <td className="max-w-md truncate">{item.stem}</td>
                  <td>{item.question_type}</td>
                  <td>{item.difficulty}</td>
                  <td>{item.status}</td>
                  <td className="space-x-2 py-2">
                    <button type="button" className="btn-secondary" onClick={() => router.push(`/question-bank/${item.id}`)}>View</button>
                    <button type="button" className="btn-primary" onClick={() => router.push(`/question-bank/${item.id}/edit`)}>Edit</button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={async () => {
                        await archiveQuestionBankItem(item.id);
                        load();
                      }}
                    >
                      Archive
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
