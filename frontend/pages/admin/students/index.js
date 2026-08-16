import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminActivateStudent,
  adminDeactivateStudent,
  adminListStudents,
  getApiErrorMessage,
  getMe,
} from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

function requireAdmin(setError, setReady) {
  return (async () => {
    if (!getToken()) {
      redirectToLogin();
      return false;
    }
    try {
      const me = await getMe();
      if (!isAdminRole(me.data.role)) {
        setError("Admin access required.");
        setReady(true);
        return false;
      }
      setReady(true);
      return true;
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return false;
      }
      setError(getApiErrorMessage(err));
      setReady(true);
      return false;
    }
  })();
}

export default function AdminStudentsPage() {
  const router = useRouter();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await adminListStudents();
      setStudents(res.data || []);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to load students."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      const ok = await requireAdmin(setError, setReady);
      if (ok) await load();
      else setLoading(false);
    })();
  }, []);

  const toggleActive = async (student) => {
    try {
      if (student.is_active) await adminDeactivateStudent(student.id);
      else await adminActivateStudent(student.id);
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="sys-tagline !text-left !text-base">Admin</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Students</h1>
        </div>
        <Link href="/admin/students/new" className="btn-primary inline-flex justify-center no-underline">
          Create Student
        </Link>
      </div>

      {loading && <p className="sys-card" role="status">Loading students…</p>}
      {!loading && error && <p className="sys-card text-red-600" role="alert">{error}</p>}
      {!loading && !error && students.length === 0 && (
        <div className="sys-card text-center">
          <p>No students yet.</p>
          <Link href="/admin/students/new" className="btn-secondary mt-4 inline-flex no-underline">
            Create Student
          </Link>
        </div>
      )}
      {!loading && !error && students.length > 0 && (
        <div className="sys-card !max-w-none overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Name</th>
                <th>Email</th>
                <th>Roll Number</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id} className="border-b">
                  <td>{s.name}</td>
                  <td>{s.email || s.institutional_email || "—"}</td>
                  <td>{s.roll_number || "—"}</td>
                  <td>{s.is_active ? s.account_status.replaceAll("_", " ") : "ACADEMICALLY INACTIVE"}</td>
                  <td className="space-x-2 py-2">
                    <button type="button" className="btn-secondary" onClick={() => router.push(`/admin/students/${s.id}`)}>
                      View
                    </button>
                    <button type="button" className="btn-primary" onClick={() => router.push(`/admin/students/${s.id}/edit`)}>
                      Edit
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => toggleActive(s)}>
                      {s.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!ready && null}
    </div>
  );
}
