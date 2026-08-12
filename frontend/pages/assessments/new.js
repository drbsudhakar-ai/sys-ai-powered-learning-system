import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminListSubjects,
  createAssessment,
  createTopic,
  getApiErrorMessage,
  getCourses,
  getMe,
  listTopics,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

const TYPES = [
  { value: "TOPIC_TEST", label: "Topic Test" },
  { value: "WEEKLY_TEST", label: "Weekly Test" },
  { value: "MONTHLY_TEST", label: "Monthly Test" },
  { value: "GRAND_TEST", label: "Grand Test" },
  { value: "FINAL_GRAND_TEST", label: "Final Grand Test" },
];

export default function NewAssessmentPage() {
  const router = useRouter();
  const presetCourse = router.query.course_id ? String(router.query.course_id) : "";
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    title: "",
    course_id: presetCourse,
    assessment_type: "TOPIC_TEST",
    duration_minutes: 60,
    total_questions: 10,
    total_marks: 40,
    marks_correct: 4,
    marks_incorrect: -1,
    marks_unanswered: 0,
    subject_id: "",
    topic_id: "",
    new_topic_name: "",
  });

  useEffect(() => {
    if (presetCourse) setForm((p) => ({ ...p, course_id: presetCourse }));
  }, [presetCourse]);

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
    if (!form.subject_id) {
      setTopics([]);
      return;
    }
    listTopics({ subject_id: form.subject_id })
      .then((res) => setTopics(res.data || []))
      .catch(() => setTopics([]));
  }, [form.subject_id]);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const courseSubjects = subjects.filter(
    (s) => !form.course_id || !s.course_id || String(s.course_id) === String(form.course_id)
  );

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      let topicId = form.topic_id ? Number(form.topic_id) : null;
      if (form.assessment_type === "TOPIC_TEST" && !topicId && form.new_topic_name.trim() && form.subject_id) {
        const t = await createTopic({
          name: form.new_topic_name.trim(),
          subject_id: Number(form.subject_id),
        });
        topicId = t.data.id;
      }
      const payload = {
        title: form.title.trim(),
        course_id: Number(form.course_id),
        assessment_type: form.assessment_type,
        duration_minutes: Number(form.duration_minutes),
        total_questions: Number(form.total_questions),
        total_marks: Number(form.total_marks),
        marks_correct: Number(form.marks_correct),
        marks_incorrect: Number(form.marks_incorrect),
        marks_unanswered: Number(form.marks_unanswered),
        subject_id: form.subject_id ? Number(form.subject_id) : null,
        topic_id: topicId,
      };
      const res = await createAssessment(payload);
      router.push(`/assessments/${res.data.id}/edit`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to create assessment."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/assessments" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to assessments
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Create Assessment</h1>
      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-4 !max-w-none">
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div>
          <label htmlFor="title" className="mb-1 block text-sm font-semibold">Title *</label>
          <input id="title" name="title" className="input-field" value={form.title} onChange={onChange} required />
        </div>
        <div>
          <label htmlFor="course_id" className="mb-1 block text-sm font-semibold">Course *</label>
          <select id="course_id" name="course_id" className="input-field" value={form.course_id} onChange={onChange} required>
            <option value="">Select course…</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="assessment_type" className="mb-1 block text-sm font-semibold">Assessment Type *</label>
          <select id="assessment_type" name="assessment_type" className="input-field" value={form.assessment_type} onChange={onChange}>
            {TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        {(form.assessment_type === "TOPIC_TEST") && (
          <>
            <div>
              <label htmlFor="subject_id" className="mb-1 block text-sm font-semibold">Subject *</label>
              <select id="subject_id" name="subject_id" className="input-field" value={form.subject_id} onChange={onChange} required>
                <option value="">Select subject…</option>
                {courseSubjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="topic_id" className="mb-1 block text-sm font-semibold">Topic</label>
              <select id="topic_id" name="topic_id" className="input-field" value={form.topic_id} onChange={onChange}>
                <option value="">Select topic…</option>
                {topics.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="new_topic_name" className="mb-1 block text-sm font-semibold">Or create topic</label>
              <input id="new_topic_name" name="new_topic_name" className="input-field" value={form.new_topic_name} onChange={onChange} placeholder="New topic name" />
            </div>
          </>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="duration_minutes" className="mb-1 block text-sm font-semibold">Duration (minutes)</label>
            <input id="duration_minutes" name="duration_minutes" type="number" min={1} className="input-field" value={form.duration_minutes} onChange={onChange} required />
          </div>
          <div>
            <label htmlFor="total_questions" className="mb-1 block text-sm font-semibold">Total questions</label>
            <input id="total_questions" name="total_questions" type="number" min={1} className="input-field" value={form.total_questions} onChange={onChange} required />
          </div>
          <div>
            <label htmlFor="total_marks" className="mb-1 block text-sm font-semibold">Total marks</label>
            <input id="total_marks" name="total_marks" type="number" min={1} className="input-field" value={form.total_marks} onChange={onChange} required />
          </div>
          <div>
            <label htmlFor="marks_correct" className="mb-1 block text-sm font-semibold">Marks correct</label>
            <input id="marks_correct" name="marks_correct" type="number" className="input-field" value={form.marks_correct} onChange={onChange} />
          </div>
          <div>
            <label htmlFor="marks_incorrect" className="mb-1 block text-sm font-semibold">Marks incorrect</label>
            <input id="marks_incorrect" name="marks_incorrect" type="number" className="input-field" value={form.marks_incorrect} onChange={onChange} />
          </div>
          <div>
            <label htmlFor="marks_unanswered" className="mb-1 block text-sm font-semibold">Marks unanswered</label>
            <input id="marks_unanswered" name="marks_unanswered" type="number" className="input-field" value={form.marks_unanswered} onChange={onChange} />
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create & Configure Blueprint"}
        </button>
      </form>
    </div>
  );
}
