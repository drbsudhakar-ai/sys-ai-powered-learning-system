import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  deleteCourse,
  enrollInCourse,
  getApiErrorMessage,
  getCourse,
  getMe,
  getMyProgrammes,
} from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function CourseDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [user, setUser] = useState(null);
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    if (!router.isReady) return;
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    if (!id) return;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const me = await getMe();
        setUser(me.data);
        const res = await getCourse(id);
        setCourse(res.data);
        if ((me.data.role || "").toLowerCase() === "student") {
          const mine = await getMyProgrammes();
          setEnrolled((mine.data.enrollments || []).some((c) => String(c.id) === String(id)));
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err, "Unable to load course."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [router.isReady, id]);

  const staff = isStaffRole(user?.role);

  const onDelete = async () => {
    if (!course) return;
    const ok = window.confirm(`Delete course "${course.title}"? This cannot be undone.`);
    if (!ok) return;
    setDeleting(true);
    setError("");
    try {
      await deleteCourse(course.id);
      router.push("/courses");
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to delete course."));
      setDeleting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <Link href="/courses" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to courses
      </Link>

      {loading && (
        <p className="sys-card mt-6" role="status">
          Loading course…
        </p>
      )}

      {!loading && error && (
        <p className="sys-card mt-6 text-red-600" role="alert">
          {error}
        </p>
      )}

      {!loading && course && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">{course.title}</h1>
          <p className="mt-3 whitespace-pre-wrap text-[var(--sys-gray)]">
            {course.description || "No description provided."}
          </p>

          <dl className="mt-6 space-y-2 text-sm text-[var(--sys-gray)]">
            <div>
              <dt className="font-semibold text-[var(--sys-blue)]">Programme category</dt>
              <dd>{(course.programme_category || "").replaceAll("_", " ") || "—"}</dd>
            </div>
            {course.examination_name ? (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Examination</dt>
                <dd>
                  {course.examination_name}
                  {course.examination_authority ? ` · ${course.examination_authority}` : ""}
                </dd>
              </div>
            ) : null}
            {course.target_purpose ? (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Purpose</dt>
                <dd>{course.target_purpose}</dd>
              </div>
            ) : null}
            {course.programme_code === "ENGLISH_COMMUNICATION" ? (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Independent programme</dt>
                <dd>English Communication (agent not included in this release)</dd>
              </div>
            ) : null}
            {course.syllabus_url && (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Syllabus</dt>
                <dd>
                  <a href={course.syllabus_url} className="break-all text-[var(--sys-blue)] underline" target="_blank" rel="noreferrer">
                    {course.syllabus_url}
                  </a>
                </dd>
              </div>
            )}
            {course.resources_url && (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Resources</dt>
                <dd>
                  <a href={course.resources_url} className="break-all text-[var(--sys-blue)] underline" target="_blank" rel="noreferrer">
                    {course.resources_url}
                  </a>
                </dd>
              </div>
            )}
            <div>
              <dt className="font-semibold text-[var(--sys-blue)]">Course Coordinators</dt>
              <dd>
                {(course.course_coordinators || []).length === 0
                  ? "None assigned"
                  : (course.course_coordinators || []).map((c) => c.faculty_name).join(", ")}
              </dd>
            </div>
            {course.created_at && (
              <div>
                <dt className="font-semibold text-[var(--sys-blue)]">Created</dt>
                <dd>{new Date(course.created_at).toLocaleString()}</dd>
              </div>
            )}
          </dl>

          {!staff && (user?.role || "").toLowerCase() === "student" && (
            <div className="mt-6">
              <button
                type="button"
                className="btn-primary"
                disabled={enrolled || enrolling}
                onClick={async () => {
                  setEnrolling(true);
                  setError("");
                  try {
                    await enrollInCourse(course.id);
                    setEnrolled(true);
                  } catch (err) {
                    setError(getApiErrorMessage(err, "Unable to enroll."));
                  } finally {
                    setEnrolling(false);
                  }
                }}
              >
                {enrolled ? "Enrolled" : "Enroll in this programme"}
              </button>
            </div>
          )}

          {staff && (
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={`/courses/${course.id}/edit`} className="btn-primary no-underline">
                Edit Course
              </Link>
              <Link href={`/assessments?course_id=${course.id}`} className="btn-secondary no-underline">
                View Assessments
              </Link>
              <Link href={`/assessments/new?course_id=${course.id}`} className="btn-secondary no-underline">
                Create Assessment
              </Link>
              <button type="button" className="btn-secondary" onClick={onDelete} disabled={deleting} aria-label="Delete course">
                {deleting ? "Deleting…" : "Delete Course"}
              </button>
            </div>
          )}
        </article>
      )}
    </div>
  );
}
