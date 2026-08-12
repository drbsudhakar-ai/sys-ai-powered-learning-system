import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  downloadAnswerKeyPdf,
  getApiErrorMessage,
  getMe,
  listStudentAssessments,
} from "../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../src/auth";

function Section({ title, items, onStart, onResume, onResult, onAnswerKey }) {
  return (
    <section className="sys-card mt-4 !max-w-none">
      <h2 className="font-bold text-[var(--sys-blue)]">{title}</h2>
      {!items?.length && <p className="mt-2 text-sm text-[var(--sys-gray)]">None</p>}
      <ul className="mt-3 space-y-3">
        {items.map((a) => (
          <li key={a.assessment_id} className="border-b pb-3 text-sm">
            <p className="font-semibold">{a.title}</p>
            <p className="text-[var(--sys-gray)]">
              {a.assessment_type} · {a.total_questions} Q · {a.duration_minutes} min · {a.total_marks} marks
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {onStart && !a.in_progress_attempt_id && (
                <button type="button" className="btn-primary" onClick={() => onStart(a)}>Start</button>
              )}
              {a.in_progress_attempt_id && onResume && (
                <button type="button" className="btn-primary" onClick={() => onResume(a)}>Resume</button>
              )}
              {a.latest_result_attempt_id && onResult && (
                <button type="button" className="btn-secondary" onClick={() => onResult(a)}>
                  Result {a.latest_percentage != null ? `(${a.latest_percentage}%)` : ""}
                </button>
              )}
              {a.answer_key_available && onAnswerKey && (
                <button type="button" className="btn-secondary" onClick={() => onAnswerKey(a)}>
                  Download Answer Key
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function StudentAssessmentsPage() {
  const router = useRouter();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const me = await getMe();
      if ((me.data.role || "").toLowerCase() !== "student") {
        setError("Student access required.");
        return;
      }
      const res = await listStudentAssessments();
      setData(res.data);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    if (!getToken()) return redirectToLogin();
    load();
  }, []);

  const downloadKey = async (a) => {
    try {
      const res = await downloadAnswerKeyPdf(a.assessment_id);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const el = document.createElement("a");
      el.href = url;
      el.download = `sys_answer_key_a${a.assessment_id}.pdf`;
      el.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Student</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">My Assessments</h1>
      {error && <p className="sys-card mt-4 text-red-600" role="alert">{error}</p>}
      {data && (
        <>
          <Section
            title="In Progress"
            items={data.in_progress}
            onResume={(a) => router.push(`/student/attempts/${a.in_progress_attempt_id}`)}
          />
          <Section
            title="Available"
            items={data.available}
            onStart={(a) => router.push(`/student/assessments/${a.assessment_id}/start`)}
          />
          <Section title="Upcoming" items={data.upcoming} />
          <Section
            title="Completed"
            items={data.completed}
            onResult={(a) => router.push(`/student/attempts/${a.latest_result_attempt_id}/result`)}
            onAnswerKey={downloadKey}
          />
        </>
      )}
      <p className="mt-6 text-sm">
        <Link href="/courses" className="text-[var(--sys-blue)] no-underline hover:underline">Courses</Link>
      </p>
    </div>
  );
}
