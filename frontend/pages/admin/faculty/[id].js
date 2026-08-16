import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminActivateFaculty,
  adminAssignCourseCoordinator,
  adminAssignSubjectExpert,
  adminCreateSubject,
  adminDeactivateFaculty,
  adminGetFaculty,
  adminListSubjects,
  adminRemoveCourseCoordinator,
  adminRemoveSubjectExpert,
  getApiErrorMessage,
  getCourses,
  getMe,
} from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function FacultyDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState(null);
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [newSubjectName, setNewSubjectName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const [fac, crs, sub] = await Promise.all([
      adminGetFaculty(id),
      getCourses(),
      adminListSubjects(),
    ]);
    setData(fac.data);
    setCourses(crs.data || []);
    setSubjects(sub.data || []);
  };

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isAdminRole(me.data.role)) {
          setError("Admin access required.");
          setLoading(false);
          return;
        }
        await refresh();
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

  const faculty = data?.faculty;

  const assignCoordinator = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await adminAssignCourseCoordinator({
        faculty_id: Number(id),
        course_id: Number(courseId),
      });
      setSuccess("Course Coordinator assigned.");
      setCourseId("");
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const assignExpert = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await adminAssignSubjectExpert({
        faculty_id: Number(id),
        subject_id: Number(subjectId),
      });
      setSuccess("Subject Expert assigned.");
      setSubjectId("");
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  const createSubject = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await adminCreateSubject({ name: newSubjectName.trim() });
      setNewSubjectName("");
      setSubjects((prev) => [...prev, res.data]);
      setSubjectId(String(res.data.id));
      setSuccess("Subject created.");
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <Link href="/admin/faculty" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to faculty
      </Link>
      {loading && <p className="sys-card mt-6">Loading…</p>}
      {!loading && error && <p className="sys-card mt-6 text-red-600" role="alert">{error}</p>}
      {!loading && faculty && (
        <>
          <article className="sys-card mt-6 !max-w-none">
            <h1 className="text-2xl font-bold text-[var(--sys-blue)]">{faculty.name}</h1>
            {success && <p className="mt-2 text-sm text-green-700" role="status">{success}</p>}
            <dl className="mt-4 space-y-2 text-sm">
              <div><dt className="font-semibold text-[var(--sys-blue)]">Login Email</dt><dd>{faculty.email || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Institutional Email</dt><dd>{faculty.institutional_email || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Institutional Mobile</dt><dd>{faculty.institutional_mobile || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Verified Personal Mobile</dt><dd>{faculty.mobile_number || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Employee Code</dt><dd>{faculty.employee_code || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">System Role</dt><dd>FACULTY</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Account Status</dt><dd>{faculty.account_status?.replaceAll("_", " ") || "—"}</dd></div>
              <div><dt className="font-semibold text-[var(--sys-blue)]">Academic Status</dt><dd>{faculty.is_active ? "Active" : "Inactive"}</dd></div>
            </dl>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href={`/admin/faculty/${faculty.id}/edit`} className="btn-primary no-underline">Edit</Link>
              <button
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  try {
                    const res = faculty.is_active
                      ? await adminDeactivateFaculty(faculty.id)
                      : await adminActivateFaculty(faculty.id);
                    setData((prev) => ({ ...prev, faculty: res.data }));
                    setSuccess(faculty.is_active ? "Faculty deactivated." : "Faculty activated.");
                    setError("");
                  } catch (err) {
                    setError(getApiErrorMessage(err));
                  }
                }}
              >
                {faculty.is_active ? "Deactivate" : "Activate"}
              </button>
            </div>
          </article>

          <section className="sys-card mt-6 !max-w-none">
            <h2 className="text-lg font-bold text-[var(--sys-blue)]">Academic Responsibilities</h2>
            <h3 className="mt-4 font-semibold">Course Coordinator</h3>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {(data.course_coordinator_assignments || []).length === 0 && <li>None assigned</li>}
              {(data.course_coordinator_assignments || []).map((a) => (
                <li key={a.id} className="mb-1 flex flex-wrap items-center gap-2">
                  <span>{a.course_title}</span>
                  <button
                    type="button"
                    className="btn-secondary !px-2 !py-1 text-xs"
                    onClick={async () => {
                      await adminRemoveCourseCoordinator(a.id);
                      await refresh();
                    }}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={assignCoordinator} className="mt-3 flex flex-wrap gap-2">
              <label htmlFor="courseId" className="sr-only">Course</label>
              <select
                id="courseId"
                className="input-field max-w-xs"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                required
                aria-label="Select course for Course Coordinator"
              >
                <option value="">Select course…</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
              <button type="submit" className="btn-primary">Assign Course Coordinator</button>
            </form>

            <h3 className="mt-6 font-semibold">Subject Expert</h3>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {(data.subject_expert_assignments || []).length === 0 && <li>None assigned</li>}
              {(data.subject_expert_assignments || []).map((a) => (
                <li key={a.id} className="mb-1 flex flex-wrap items-center gap-2">
                  <span>{a.subject_name}</span>
                  <button
                    type="button"
                    className="btn-secondary !px-2 !py-1 text-xs"
                    onClick={async () => {
                      await adminRemoveSubjectExpert(a.id);
                      await refresh();
                    }}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={createSubject} className="mt-3 flex flex-wrap gap-2">
              <label htmlFor="newSubject" className="sr-only">New subject name</label>
              <input
                id="newSubject"
                className="input-field max-w-xs"
                placeholder="New subject name"
                value={newSubjectName}
                onChange={(e) => setNewSubjectName(e.target.value)}
                required
              />
              <button type="submit" className="btn-secondary">Create Subject</button>
            </form>
            <form onSubmit={assignExpert} className="mt-3 flex flex-wrap gap-2">
              <label htmlFor="subjectId" className="sr-only">Subject</label>
              <select
                id="subjectId"
                className="input-field max-w-xs"
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                required
                aria-label="Select subject for Subject Expert"
              >
                <option value="">Select subject…</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <button type="submit" className="btn-primary">Assign Subject Expert</button>
            </form>
          </section>
        </>
      )}
    </div>
  );
}
