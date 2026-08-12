import { useEffect, useState } from "react";
import Link from "next/link";
import {
  adminListSubjects,
  createHistoricalPaper,
  getApiErrorMessage,
  getCourses,
  getMe,
  listHistoricalPapers,
  listTopics,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function HistoricalPapersPage() {
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [papers, setPapers] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    exam_name: "",
    exam_year: new Date().getFullYear(),
    subject_id: "",
    topic_id: "",
    question_text: "",
    marks: 4,
    difficulty: "MEDIUM",
    concept_tags: "",
  });

  const load = async (cid) => {
    const res = await listHistoricalPapers({ course_id: cid });
    setPapers(res.data || []);
  };

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

  useEffect(() => {
    if (!form.subject_id) return setTopics([]);
    listTopics({ subject_id: form.subject_id }).then((r) => setTopics(r.data || [])).catch(() => setTopics([]));
  }, [form.subject_id]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await createHistoricalPaper({
        exam_name: form.exam_name,
        exam_year: Number(form.exam_year),
        course_id: Number(courseId),
        exam_type: "ENTRANCE",
        questions: [
          {
            subject_id: Number(form.subject_id),
            topic_id: form.topic_id ? Number(form.topic_id) : null,
            question_text: form.question_text,
            marks: Number(form.marks),
            difficulty: form.difficulty,
            concept_tags: form.concept_tags.split(",").map((t) => t.trim()).filter(Boolean),
            similarity_class: "CONCEPT_VARIANT",
          },
        ],
      });
      setForm((p) => ({ ...p, question_text: "", exam_name: "" }));
      await load(courseId);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <Link href="/question-bank" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">← Question Bank</Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Historical Question Papers</h1>

      <div className="sys-card mt-6 !max-w-none">
        <label htmlFor="courseId" className="mb-1 block text-sm font-semibold">Course</label>
        <select
          id="courseId"
          className="input-field max-w-md"
          value={courseId}
          onChange={async (e) => {
            setCourseId(e.target.value);
            if (e.target.value) await load(e.target.value);
          }}
        >
          <option value="">Select…</option>
          {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </div>

      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}

      <form onSubmit={onSubmit} className="sys-card mt-4 space-y-3 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Add paper item</h2>
        <input className="input-field" placeholder="Exam name" required value={form.exam_name} onChange={(e) => setForm({ ...form, exam_name: e.target.value })} disabled={!courseId} />
        <input className="input-field" type="number" value={form.exam_year} onChange={(e) => setForm({ ...form, exam_year: e.target.value })} />
        <select className="input-field" required value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })}>
          <option value="">Subject…</option>
          {subjects.filter((s) => !s.course_id || String(s.course_id) === String(courseId)).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select className="input-field" value={form.topic_id} onChange={(e) => setForm({ ...form, topic_id: e.target.value })}>
          <option value="">Topic…</option>
          {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <textarea className="input-field min-h-[80px]" required placeholder="Historical question text" value={form.question_text} onChange={(e) => setForm({ ...form, question_text: e.target.value })} />
        <input className="input-field" placeholder="Concepts (comma)" value={form.concept_tags} onChange={(e) => setForm({ ...form, concept_tags: e.target.value })} />
        <button type="submit" className="btn-primary" disabled={!courseId}>Save Historical Item</button>
      </form>

      <section className="sys-card mt-4 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Papers</h2>
        <ul className="mt-2 list-disc pl-5 text-sm">
          {papers.map((p) => (
            <li key={p.id}>{p.exam_year} — {p.exam_name}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
