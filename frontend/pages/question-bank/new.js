import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminListSubjects,
  checkQuestionSimilarity,
  createQuestionBankItem,
  getApiErrorMessage,
  getCourses,
  getMe,
  listTopics,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function NewQuestionPage() {
  const router = useRouter();
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [dupWarn, setDupWarn] = useState("");
  const [form, setForm] = useState({
    course_id: "",
    subject_id: "",
    topic_id: "",
    stem: "",
    question_type: "SINGLE_MCQ",
    difficulty: "MEDIUM",
    status: "DRAFT",
    options_text: "A\nB\nC\nD",
    correct_answer: "",
    explanation: "",
    marks: 4,
    negative_marks: -1,
    shortcut: "",
    common_traps: "",
    alternative_solution: "",
    concept_tags: "",
    quality_score: 0.8,
    estimated_time_seconds: 90,
  });

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) setError("Staff access required.");
        const [crs, subs] = await Promise.all([getCourses(), adminListSubjects()]);
        setCourses(crs.data || []);
        setSubjects(subs.data || []);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        }
      }
    })();
  }, []);

  useEffect(() => {
    if (!form.subject_id) return setTopics([]);
    listTopics({ subject_id: form.subject_id }).then((r) => setTopics(r.data || [])).catch(() => setTopics([]));
  }, [form.subject_id]);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setDupWarn("");
    try {
      const sim = await checkQuestionSimilarity({ course_id: Number(form.course_id), text: form.stem });
      if ((sim.data.matches || []).some((m) => m.class === "EXACT_PREVIOUS")) {
        setError("Exact duplicate exists in the bank.");
        return;
      }
      if ((sim.data.matches || []).length) {
        setDupWarn(`Near-duplicate warning: ${sim.data.matches.length} similar question(s).`);
      }
      const options = form.options_text.split("\n").map((s) => s.trim()).filter(Boolean);
      const res = await createQuestionBankItem({
        stem: form.stem.trim(),
        course_id: Number(form.course_id),
        subject_id: Number(form.subject_id),
        topic_id: form.topic_id ? Number(form.topic_id) : null,
        question_type: form.question_type,
        difficulty: form.difficulty,
        status: form.status,
        options,
        correct_answer: form.correct_answer || null,
        explanation: form.explanation || null,
        marks: Number(form.marks),
        negative_marks: Number(form.negative_marks),
        shortcut: form.shortcut || null,
        common_traps: form.common_traps || null,
        alternative_solution: form.alternative_solution || null,
        concept_tags: form.concept_tags ? form.concept_tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
        quality_score: Number(form.quality_score),
        estimated_time_seconds: Number(form.estimated_time_seconds),
      });
      router.push(`/question-bank/${res.data.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const courseSubjects = subjects.filter(
    (s) => !form.course_id || !s.course_id || String(s.course_id) === String(form.course_id)
  );

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/question-bank" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">← Question Bank</Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Create Question</h1>
      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-3 !max-w-none">
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        {dupWarn && <p className="text-sm text-amber-700">{dupWarn}</p>}
        <div>
          <label htmlFor="course_id" className="mb-1 block text-sm font-semibold">Course</label>
          <select id="course_id" name="course_id" className="input-field" required value={form.course_id} onChange={onChange}>
            <option value="">Select…</option>
            {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="subject_id" className="mb-1 block text-sm font-semibold">Subject</label>
          <select id="subject_id" name="subject_id" className="input-field" required value={form.subject_id} onChange={onChange}>
            <option value="">Select…</option>
            {courseSubjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="topic_id" className="mb-1 block text-sm font-semibold">Topic</label>
          <select id="topic_id" name="topic_id" className="input-field" value={form.topic_id} onChange={onChange}>
            <option value="">Optional…</option>
            {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="stem" className="mb-1 block text-sm font-semibold">Question</label>
          <textarea id="stem" name="stem" className="input-field min-h-[100px]" required value={form.stem} onChange={onChange} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="question_type" className="mb-1 block text-sm font-semibold">Type</label>
            <select id="question_type" name="question_type" className="input-field" value={form.question_type} onChange={onChange}>
              <option value="SINGLE_MCQ">Single MCQ</option>
              <option value="MULTI_MCQ">Multi MCQ</option>
              <option value="TRUE_FALSE">True/False</option>
              <option value="FILL_BLANK">Fill blank</option>
            </select>
          </div>
          <div>
            <label htmlFor="difficulty" className="mb-1 block text-sm font-semibold">Difficulty</label>
            <select id="difficulty" name="difficulty" className="input-field" value={form.difficulty} onChange={onChange}>
              {["EASY", "MEDIUM", "HARD", "ADVANCED"].map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label htmlFor="options_text" className="mb-1 block text-sm font-semibold">Options (one per line)</label>
          <textarea id="options_text" name="options_text" className="input-field min-h-[90px]" value={form.options_text} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="correct_answer" className="mb-1 block text-sm font-semibold">Correct answer</label>
          <input id="correct_answer" name="correct_answer" className="input-field" value={form.correct_answer} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="explanation" className="mb-1 block text-sm font-semibold">Explanation</label>
          <textarea id="explanation" name="explanation" className="input-field" value={form.explanation} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="shortcut" className="mb-1 block text-sm font-semibold">Shortcut</label>
          <textarea id="shortcut" name="shortcut" className="input-field" value={form.shortcut} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="common_traps" className="mb-1 block text-sm font-semibold">Common traps</label>
          <textarea id="common_traps" name="common_traps" className="input-field" value={form.common_traps} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="concept_tags" className="mb-1 block text-sm font-semibold">Concept tags (comma-separated)</label>
          <input id="concept_tags" name="concept_tags" className="input-field" value={form.concept_tags} onChange={onChange} />
        </div>
        <button type="submit" className="btn-primary">Save Question</button>
      </form>
    </div>
  );
}
