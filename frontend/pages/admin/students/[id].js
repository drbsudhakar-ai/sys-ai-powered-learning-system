import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminActivateStudent,
  adminDeactivateStudent,
  adminGetStudent,
  getApiErrorMessage,
  getMe,
} from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function StudentDetailsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [student, setStudent] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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
        const res = await adminGetStudent(id);
        setStudent(res.data);
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

  const toggle = async () => {
    try {
      const res = student.is_active
        ? await adminDeactivateStudent(student.id)
        : await adminActivateStudent(student.id);
      setStudent(res.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/admin/students" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to students
      </Link>
      {loading && <p className="sys-card mt-6" role="status">Loading…</p>}
      {!loading && error && <p className="sys-card mt-6 text-red-600" role="alert">{error}</p>}
      {!loading && student && (
        <article className="sys-card mt-6 !max-w-none">
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">{student.name}</h1>
          <dl className="mt-4 space-y-2 text-sm">
            <div><dt className="font-semibold text-[var(--sys-blue)]">Login Email</dt><dd>{student.email || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Institutional Email</dt><dd>{student.institutional_email || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Institutional Mobile</dt><dd>{student.institutional_mobile || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Verified Personal Mobile</dt><dd>{student.mobile_number || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Roll Number</dt><dd>{student.roll_number || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">System Role</dt><dd>{student.role}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Account Status</dt><dd>{student.account_status?.replaceAll("_", " ") || "—"}</dd></div>
            <div><dt className="font-semibold text-[var(--sys-blue)]">Academic Status</dt><dd>{student.is_active ? "Active" : "Inactive"}</dd></div>
          </dl>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href={`/admin/students/${student.id}/edit`} className="btn-primary no-underline">Edit</Link>
            <button type="button" className="btn-secondary" onClick={toggle}>
              {student.is_active ? "Deactivate" : "Activate"}
            </button>
          </div>
        </article>
      )}
    </div>
  );
}
