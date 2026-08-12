import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  duplicateQuestionBankItem,
  getApiErrorMessage,
  getMe,
  getQuestionBankItem,
  getQuestionImportance,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function QuestionDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [item, setItem] = useState(null);
  const [importance, setImportance] = useState(null);
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
        setItem(res.data);
        try {
          const imp = await getQuestionImportance(id);
          setImportance(imp.data);
        } catch (_) {
          /* optional */
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id]);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <Link href="/question-bank" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">← Question Bank</Link>
      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}
      {item && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-xl font-bold text-[var(--sys-blue)]">Question Preview</h1>
          <p className="mt-4 whitespace-pre-wrap">{item.stem}</p>
          {item.options?.length > 0 && (
            <ul className="mt-3 list-disc pl-5 text-sm">
              {item.options.map((o) => <li key={o}>{o}</li>)}
            </ul>
          )}
          <dl className="mt-4 space-y-2 text-sm">
            <div><dt className="font-semibold text-[var(--sys-blue)]">Type / Difficulty / Status</dt><dd>{item.question_type} · {item.difficulty} · {item.status}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Answer</dt><dd>{item.correct_answer || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Explanation</dt><dd>{item.explanation || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Shortcut</dt><dd>{item.shortcut || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Common traps</dt><dd>{item.common_traps || "—"}</dd></div>
          </dl>
          {importance && (
            <div className="mt-4 rounded border border-[var(--sys-blue)]/20 p-3 text-sm">
              <p className="font-semibold text-[var(--sys-blue)]">Importance: {importance.importance_score}</p>
              <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(importance.contributing_factors, null, 2)}</pre>
              <p className="mt-2 text-xs text-[var(--sys-gray)]">{importance.disclaimer}</p>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href={`/question-bank/${item.id}/edit`} className="btn-primary no-underline">Edit</Link>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                const res = await duplicateQuestionBankItem(item.id);
                router.push(`/question-bank/${res.data.id}/edit`);
              }}
            >
              Duplicate
            </button>
          </div>
        </article>
      )}
    </div>
  );
}
