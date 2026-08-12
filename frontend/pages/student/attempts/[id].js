import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import {
  getApiErrorMessage,
  getAttempt,
  getMe,
  saveAttemptResponse,
  submitAttempt,
} from "../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../src/auth";

function formatTime(sec) {
  const s = Math.max(0, Number(sec) || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export default function LiveAttemptPage() {
  const router = useRouter();
  const { id } = router.query;
  const [attempt, setAttempt] = useState(null);
  const [index, setIndex] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const lastSpend = useRef(Date.now());

  const refresh = useCallback(async () => {
    const res = await getAttempt(id);
    setAttempt(res.data);
    setRemaining(res.data.remaining_seconds || 0);
    if (res.data.status !== "IN_PROGRESS") {
      router.replace(`/student/attempts/${id}/result`);
    }
    return res.data;
  }, [id, router]);

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if ((me.data.role || "").toLowerCase() !== "student") {
          setError("Student access required.");
          return;
        }
        await refresh();
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id, refresh]);

  useEffect(() => {
    if (!attempt || attempt.status !== "IN_PROGRESS") return undefined;
    const t = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(t);
          submitAttempt(id)
            .then(() => router.replace(`/student/attempts/${id}/result`))
            .catch(() => refresh());
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [attempt, id, refresh, router]);

  const q = attempt?.questions?.[index];

  const persist = async (payload) => {
    if (!q) return;
    setSaving(true);
    setError("");
    const delta = (Date.now() - lastSpend.current) / 1000;
    lastSpend.current = Date.now();
    try {
      await saveAttemptResponse(id, {
        assessment_question_id: q.assessment_question_id,
        time_spent_delta: delta,
        ...payload,
      });
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
      if (err.response?.status === 400) await refresh();
    } finally {
      setSaving(false);
    }
  };

  const onSubmit = async () => {
    setError("");
    try {
      await submitAttempt(id);
      router.replace(`/student/attempts/${id}/result`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  if (!attempt) {
    return <p className="sys-card mx-auto mt-8 max-w-3xl">{error || "Loading attempt…"}</p>;
  }

  const summary = attempt.summary || {};

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      <div className="sys-card !max-w-none flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--sys-gray)]">Attempt #{attempt.attempt_id}</p>
          <p className="font-bold text-[var(--sys-blue)]">Live Assessment</p>
        </div>
        <p className="text-xl font-bold tabular-nums" aria-live="polite">{formatTime(remaining)}</p>
      </div>

      {error && <p className="mt-3 text-sm text-red-600" role="alert">{error}</p>}
      {saving && <p className="mt-2 text-xs text-[var(--sys-gray)]">Saving…</p>}

      {q && (
        <article className="sys-card mt-4 !max-w-none">
          <h1 className="text-lg font-bold text-[var(--sys-blue)]">
            Question {q.sequence}
            <span className="ml-2 text-sm font-normal text-[var(--sys-gray)]">({q.marks} marks)</span>
          </h1>
          <p className="mt-3 whitespace-pre-wrap">{q.stem}</p>
          <div className="mt-4 space-y-2">
            {(q.options || []).map((opt) => (
              <label key={opt} className="flex cursor-pointer items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="answer"
                  checked={q.selected_answer === opt}
                  onChange={() => persist({ selected_answer: opt })}
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => persist({ clear: true })}>Clear</button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => persist({ marked_for_review: !q.marked_for_review })}
            >
              {q.marked_for_review ? "Unmark Review" : "Mark Review"}
            </button>
            <button type="button" className="btn-secondary" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
              Previous
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={index >= (attempt.questions?.length || 1) - 1}
              onClick={() => setIndex((i) => i + 1)}
            >
              Next
            </button>
            <button type="button" className="btn-primary" onClick={() => setConfirmSubmit(true)}>Submit</button>
          </div>
        </article>
      )}

      <div className="sys-card mt-4 !max-w-none">
        <p className="text-sm font-semibold">Question palette</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(attempt.questions || []).map((item, i) => {
            let cls = "btn-secondary !px-2 !py-1 text-xs";
            if (i === index) cls = "btn-primary !px-2 !py-1 text-xs";
            else if (item.marked_for_review) cls += " ring-2 ring-amber-400";
            else if (item.answered) cls += " !bg-green-100";
            return (
              <button key={item.assessment_question_id} type="button" className={cls} onClick={() => setIndex(i)}>
                {item.sequence}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-sm text-[var(--sys-gray)]">
          Answered {summary.answered} · Unanswered {summary.unanswered} · Marked {summary.marked_review} · Total {summary.total}
        </p>
      </div>

      {confirmSubmit && (
        <div className="sys-card mt-4 !max-w-none" role="dialog" aria-modal="true">
          <h2 className="font-bold text-[var(--sys-blue)]">Confirm submission</h2>
          <p className="mt-2 text-sm">
            Answered: {summary.answered} · Unanswered: {summary.unanswered} · Marked review: {summary.marked_review} · Total: {summary.total}
          </p>
          <div className="mt-4 flex gap-2">
            <button type="button" className="btn-primary" onClick={onSubmit}>Confirm Submit</button>
            <button type="button" className="btn-secondary" onClick={() => setConfirmSubmit(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
