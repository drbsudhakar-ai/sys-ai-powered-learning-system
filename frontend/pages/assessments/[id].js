import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  archiveAssessment,
  getApiErrorMessage,
  getAssessment,
  getMe,
  publishAssessment,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function AssessmentDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [user, setUser] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        setUser(me.data);
        const res = await getAssessment(id);
        setAssessment(res.data);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [router.isReady, id]);

  const staff = isStaffRole(user?.role);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <Link href="/assessments" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to assessments
      </Link>
      {loading && <p className="sys-card mt-6">Loading…</p>}
      {!loading && error && <p className="sys-card mt-6 text-red-600" role="alert">{error}</p>}
      {!loading && assessment && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">{assessment.title}</h1>
          {message && <p className="mt-2 text-sm text-green-700">{message}</p>}
          <dl className="mt-4 space-y-2 text-sm">
            <div><dt className="font-semibold text-[var(--sys-blue)]">Type</dt><dd>{assessment.assessment_type}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Category</dt><dd>{assessment.category}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Status</dt><dd>{assessment.status}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Duration</dt><dd>{assessment.duration_minutes} min</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Questions / Marks</dt><dd>{assessment.total_questions} / {assessment.total_marks}</dd></div>
            <div>
              <dt className="font-semibold text-[var(--sys-blue)]">Marking</dt>
              <dd>+{assessment.marks_correct} / {assessment.marks_incorrect} / {assessment.marks_unanswered}</dd>
            </div>
          </dl>

          <h2 className="mt-6 font-bold text-[var(--sys-blue)]">Blueprint</h2>
          {(assessment.blueprint_items || []).length === 0 ? (
            <p className="text-sm text-[var(--sys-gray)]">No blueprint configured.</p>
          ) : (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {assessment.blueprint_items.map((b) => (
                <li key={b.id}>
                  Subject {b.subject_id}
                  {b.topic_id ? ` / Topic ${b.topic_id}` : ""} — {b.difficulty}: {b.question_count}
                </li>
              ))}
            </ul>
          )}

          <h2 className="mt-6 font-bold text-[var(--sys-blue)]">Published Versions</h2>
          {(assessment.versions || []).length === 0 ? (
            <p className="text-sm text-[var(--sys-gray)]">No published versions yet.</p>
          ) : (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {assessment.versions.map((v) => (
                <li key={v.id}>
                  v{v.version_number} — {v.questions?.length || v.total_questions || 0} questions
                </li>
              ))}
            </ul>
          )}

          {staff && (
            <div className="mt-6 flex flex-wrap gap-3">
              {assessment.status === "DRAFT" && (
                <Link href={`/assessments/${assessment.id}/edit`} className="btn-primary no-underline">Design / Edit</Link>
              )}
              {assessment.status === "DRAFT" && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={async () => {
                    try {
                      const res = await publishAssessment(assessment.id);
                      setMessage(`Published v${res.data.version_number}`);
                      const refreshed = await getAssessment(id);
                      setAssessment(refreshed.data);
                    } catch (err) {
                      setError(getApiErrorMessage(err));
                    }
                  }}
                >
                  Publish
                </button>
              )}
              {assessment.status !== "ARCHIVED" && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={async () => {
                    await archiveAssessment(assessment.id);
                    router.push("/assessments");
                  }}
                >
                  Archive
                </button>
              )}
            </div>
          )}
        </article>
      )}
    </div>
  );
}
