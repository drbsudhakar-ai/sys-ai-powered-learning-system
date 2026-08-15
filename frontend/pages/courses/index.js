import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { getCourses, getMe, getMyProgrammes, getApiErrorMessage, enrollInCourse } from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function CoursesPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [enrolledIds, setEnrolledIds] = useState([]);
  const [enrolling, setEnrolling] = useState(null);

  useEffect(() => {
    if (!getToken()) {
      redirectToLogin();
      return;
    }

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const me = await getMe();
        setUser(me.data);
        const res = await getCourses();
        setCourses(Array.isArray(res.data) ? res.data : []);
        if ((me.data.role || "").toLowerCase() === "student") {
          const mine = await getMyProgrammes();
          setEnrolledIds((mine.data.enrollments || []).map((c) => c.id));
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err, "Unable to load courses."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const staff = isStaffRole(user?.role);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="sys-tagline !text-left !text-base">Preparation courses & learning programmes</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)] sm:text-3xl">Courses</h1>
          <p className="mt-1 text-sm text-[var(--sys-gray)]">
            Browse SYS preparation courses and independent learning programmes
            {user?.role ? ` · signed in as ${user.role}` : ""}.
          </p>
        </div>
        {staff && (
          <Link href="/courses/new" className="btn-primary inline-flex justify-center text-center no-underline">
            Create Course
          </Link>
        )}
      </div>

      {loading && (
        <p className="sys-card text-center text-[var(--sys-gray)]" role="status">
          Loading courses…
        </p>
      )}

      {!loading && error && (
        <p className="sys-card text-red-600" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && courses.length === 0 && (
        <div className="sys-card text-center">
          <p className="text-[var(--sys-gray)]">No courses available yet.</p>
          {staff && (
            <Link href="/courses/new" className="btn-secondary mt-4 inline-flex no-underline">
              Create the first course
            </Link>
          )}
        </div>
      )}

      {!loading && !error && courses.length > 0 && (
        <ul className="space-y-4" aria-label="Course list">
          {courses.map((course) => (
            <li key={course.id} className="sys-card !mx-0 !max-w-none">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-[var(--sys-blue)]">{course.title}</h2>
                  <p className="mt-1 text-sm text-[var(--sys-gray)]">
                    {course.description || "No description provided."}
                  </p>
                  <p className="mt-2 text-xs text-gray-500">
                    {(course.programme_category || "").replaceAll("_", " ")}
                    {course.examination_name ? ` · ${course.examination_name}` : ""}
                    {course.programme_code === "ENGLISH_COMMUNICATION" ? " · English Communication" : ""}
                  </p>
                  {course.created_at && (
                    <p className="mt-2 text-xs text-gray-500">
                      Created {new Date(course.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => router.push(`/courses/${course.id}`)}
                  >
                    View
                  </button>
                  {staff && (
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => router.push(`/courses/${course.id}/edit`)}
                    >
                      Edit
                    </button>
                  )}
                  {!staff && user?.role?.toLowerCase() === "student" && (
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={enrolling === course.id || enrolledIds.includes(course.id)}
                      onClick={async () => {
                        setEnrolling(course.id);
                        setError("");
                        try {
                          await enrollInCourse(course.id);
                          setEnrolledIds((prev) => [...prev, course.id]);
                        } catch (err) {
                          setError(getApiErrorMessage(err, "Unable to enroll."));
                        } finally {
                          setEnrolling(null);
                        }
                      }}
                    >
                      {enrolledIds.includes(course.id) ? "Enrolled" : "Enroll"}
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
