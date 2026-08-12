import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  downloadAnswerKeyPdf,
  getApiErrorMessage,
  getAttemptResult,
  getMe,
} from "../../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../../src/auth";

export default function AttemptResultPage() {
  const router = useRouter();
  const { id } = router.query;
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        await getMe();
        const res = await getAttemptResult(id);
        setResult(res.data);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id]);

  const downloadKey = async () => {
    try {
      const res = await downloadAnswerKeyPdf(result.assessment_id);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `sys_answer_key_a${result.assessment_id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <Link href="/student/assessments" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← My Assessments
      </Link>
      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}
      {result && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Result — {result.assessment_title}</h1>
          <p className="mt-2 text-sm">{result.assessment_type} · {result.status}{result.auto_submitted ? " (auto-submitted)" : ""}</p>
          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="font-semibold">Score</dt><dd>{result.score} / {result.total_marks}</dd></div>
            <div><dt className="font-semibold">Percentage</dt><dd>{result.percentage}%</dd></div>
            <div><dt className="font-semibold">Accuracy</dt><dd>{result.accuracy ?? "—"}%</dd></div>
            <div><dt className="font-semibold">Time spent</dt><dd>{Math.round(result.time_spent_seconds || 0)}s</dd></div>
            <div><dt className="font-semibold">Correct</dt><dd>{result.correct}</dd></div>
            <div><dt className="font-semibold">Incorrect</dt><dd>{result.incorrect}</dd></div>
            <div><dt className="font-semibold">Unanswered</dt><dd>{result.unanswered}</dd></div>
          </dl>

          <h2 className="mt-6 font-bold text-[var(--sys-blue)]">Subject performance</h2>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {(result.subject_performance || []).map((s) => (
              <li key={s.id}>{s.name}: {s.percentage}% ({s.marks_obtained}/{s.marks_available})</li>
            ))}
          </ul>
          <h2 className="mt-4 font-bold text-[var(--sys-blue)]">Topic performance</h2>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {(result.topic_performance || []).map((s) => (
              <li key={s.id}>{s.name}: {s.percentage}%</li>
            ))}
          </ul>
          <h2 className="mt-4 font-bold text-[var(--sys-blue)]">Difficulty performance</h2>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {(result.difficulty_performance || []).map((s) => (
              <li key={s.name}>{s.name}: {s.percentage}%</li>
            ))}
          </ul>

          <div className="mt-6 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={downloadKey}>Download Answer Key & Explanations</button>
            <Link href="/performance" className="btn-secondary no-underline">Performance Sheet</Link>
          </div>
        </article>
      )}
    </div>
  );
}
