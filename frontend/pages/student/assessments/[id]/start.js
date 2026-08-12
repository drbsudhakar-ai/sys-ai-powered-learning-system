import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  getApiErrorMessage,
  getAssessmentInstructions,
  getMe,
  startAssessmentAttempt,
} from "../../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../../src/auth";

export default function StartAssessmentPage() {
  const router = useRouter();
  const { id } = router.query;
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

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
        const res = await getAssessmentInstructions(id);
        setInfo(res.data);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id]);

  const start = async () => {
    setStarting(true);
    setError("");
    try {
      const res = await startAssessmentAttempt(id);
      router.replace(`/student/attempts/${res.data.attempt_id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStarting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/student/assessments" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← My Assessments
      </Link>
      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}
      {info && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">{info.title}</h1>
          <dl className="mt-4 space-y-2 text-sm">
            <div><dt className="font-semibold">Type</dt><dd>{info.assessment_type}</dd></div>
            <div><dt className="font-semibold">Duration</dt><dd>{info.duration_minutes} minutes</dd></div>
            <div><dt className="font-semibold">Questions / Marks</dt><dd>{info.total_questions} / {info.total_marks}</dd></div>
            <div><dt className="font-semibold">Marking</dt><dd>+{info.marks_correct} / {info.marks_incorrect} / {info.marks_unanswered}</dd></div>
            <div><dt className="font-semibold">Max attempts</dt><dd>{info.max_attempts}</dd></div>
          </dl>
          <p className="mt-4 text-sm text-[var(--sys-gray)]">
            The server timer is authoritative. Answers auto-save. Do not close the browser without submitting.
          </p>
          <button type="button" className="btn-primary mt-6" disabled={!info.available || starting} onClick={start}>
            {starting ? "Starting…" : info.available ? "Start Assessment" : info.availability_message}
          </button>
        </article>
      )}
    </div>
  );
}
