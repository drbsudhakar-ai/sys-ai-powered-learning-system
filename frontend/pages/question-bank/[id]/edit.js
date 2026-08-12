import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { getApiErrorMessage, getMe, getQuestionBankItem, updateQuestionBankItem } from "../../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../../src/auth";

export default function EditQuestionPage() {
  const router = useRouter();
  const { id } = router.query;
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("Staff access required.");
          return;
        }
        const res = await getQuestionBankItem(id);
        const d = res.data;
        setForm({
          stem: d.stem || "",
          difficulty: d.difficulty,
          status: d.status,
          correct_answer: d.correct_answer || "",
          explanation: d.explanation || "",
          shortcut: d.shortcut || "",
          common_traps: d.common_traps || "",
          options_text: (d.options || []).join("\n"),
          quality_score: d.quality_score ?? 0.8,
        });
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id]);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await updateQuestionBankItem(id, {
        stem: form.stem,
        difficulty: form.difficulty,
        status: form.status,
        correct_answer: form.correct_answer || null,
        explanation: form.explanation || null,
        shortcut: form.shortcut || null,
        common_traps: form.common_traps || null,
        options: form.options_text.split("\n").map((s) => s.trim()).filter(Boolean),
        quality_score: Number(form.quality_score),
      });
      router.push(`/question-bank/${id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  if (!form) return <p className="sys-card mx-auto mt-8 max-w-2xl">Loading…</p>;

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href={`/question-bank/${id}`} className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">← Back</Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Edit Question</h1>
      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-3 !max-w-none">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <textarea name="stem" className="input-field min-h-[100px]" value={form.stem} onChange={onChange} required />
        <select name="difficulty" className="input-field" value={form.difficulty} onChange={onChange}>
          {["EASY", "MEDIUM", "HARD", "ADVANCED"].map((d) => <option key={d}>{d}</option>)}
        </select>
        <select name="status" className="input-field" value={form.status} onChange={onChange}>
          {["DRAFT", "REVIEW", "APPROVED", "ACTIVE", "ARCHIVED"].map((s) => <option key={s}>{s}</option>)}
        </select>
        <textarea name="options_text" className="input-field min-h-[80px]" value={form.options_text} onChange={onChange} />
        <input name="correct_answer" className="input-field" value={form.correct_answer} onChange={onChange} placeholder="Correct answer" />
        <textarea name="explanation" className="input-field" value={form.explanation} onChange={onChange} placeholder="Explanation" />
        <textarea name="shortcut" className="input-field" value={form.shortcut} onChange={onChange} placeholder="Shortcut" />
        <textarea name="common_traps" className="input-field" value={form.common_traps} onChange={onChange} placeholder="Common traps" />
        <button type="submit" className="btn-primary">Save</button>
      </form>
    </div>
  );
}
