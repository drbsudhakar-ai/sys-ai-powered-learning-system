import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { getAssessments, getCourses, getApiErrorMessage, getMe } from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

export default function AssessmentsPage() {
  const router = useRouter();
  const courseFilter = router.query.course_id ? String(router.query.course_id) : "";
  const [user, setUser] = useState(null);
  const [courses, setCourses] = useState([]);
  const [items, setItems] = useState([]);
  const [courseId, setCourseId] = useState(courseFilter);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (courseFilter) setCourseId(courseFilter);
  }, [courseFilter]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const me = await getMe();
      setUser(me.data);
      const crs = await getCourses();
      setCourses(crs.data || []);
      const params = {};
      if (courseId) params.course_id = courseId;
      if (typeFilter) params.assessment_type = typeFilter;
      if (statusFilter) params.status = statusFilter;
      const res = await getAssessments(params);
      setItems(res.data || []);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to load assessments."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!getToken()) return redirectToLogin();
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, typeFilter, statusFilter]);

  const staff = isStaffRole(user?.role);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="sys-tagline !text-left !text-base">Assessments</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Assessment Management</h1>
        </div>
        {staff && (
          <Link
            href={courseId ? `/assessments/new?course_id=${courseId}` : "/assessments/new"}
            className="btn-primary inline-flex no-underline"
          >
            Create Assessment
          </Link>
        )}
      </div>

      <div className="sys-card mb-6 !max-w-none grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor="courseId" className="mb-1 block text-sm font-semibold">Course</label>
          <select id="courseId" className="input-field" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">All courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="typeFilter" className="mb-1 block text-sm font-semibold">Type</label>
          <select id="typeFilter" className="input-field" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All types</option>
            <option value="TOPIC_TEST">Topic Test</option>
            <option value="WEEKLY_TEST">Weekly</option>
            <option value="MONTHLY_TEST">Monthly</option>
            <option value="GRAND_TEST">Grand</option>
            <option value="FINAL_GRAND_TEST">Final Grand</option>
          </select>
        </div>
        <div>
          <label htmlFor="statusFilter" className="mb-1 block text-sm font-semibold">Status</label>
          <select id="statusFilter" className="input-field" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
            <option value="ARCHIVED">Archived</option>
          </select>
        </div>
      </div>

      {loading && <p className="sys-card" role="status">Loading assessments…</p>}
      {!loading && error && <p className="sys-card text-red-600" role="alert">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <div className="sys-card text-center">
          <p>No assessments found.</p>
          {staff && (
            <Link href="/assessments/new" className="btn-secondary mt-4 inline-flex no-underline">Create Assessment</Link>
          )}
        </div>
      )}
      {!loading && !error && items.length > 0 && (
        <div className="sys-card !max-w-none overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Title</th>
                <th>Type</th>
                <th>Category</th>
                <th>Status</th>
                <th>Questions</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b">
                  <td>{a.title}</td>
                  <td>{a.assessment_type || "—"}</td>
                  <td>{a.category || "—"}</td>
                  <td>{a.status}</td>
                  <td>{a.total_questions ?? "—"}</td>
                  <td className="space-x-2 py-2">
                    <button type="button" className="btn-secondary" onClick={() => router.push(`/assessments/${a.id}`)}>View</button>
                    {staff && a.status === "DRAFT" && (
                      <button type="button" className="btn-primary" onClick={() => router.push(`/assessments/${a.id}/edit`)}>Edit</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
