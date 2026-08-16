import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  adminActivateFaculty,
  adminDeactivateFaculty,
  adminListFaculty,
  getApiErrorMessage,
  getMe,
} from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function AdminFacultyPage() {
  const router = useRouter();
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await adminListFaculty();
      setFaculty(res.data || []);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to load faculty."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isAdminRole(me.data.role)) {
          setError("Admin access required.");
          setLoading(false);
          return;
        }
        await load();
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err));
        setLoading(false);
      }
    })();
  }, []);

  const toggleActive = async (row) => {
    try {
      if (row.is_active) await adminDeactivateFaculty(row.id);
      else await adminActivateFaculty(row.id);
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
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Faculty</h1>
        </div>
        <Link href="/admin/faculty/new" className="btn-primary inline-flex justify-center no-underline">
          Create Faculty
        </Link>
      </div>
      {loading && <p className="sys-card" role="status">Loading faculty…</p>}
      {!loading && error && <p className="sys-card text-red-600" role="alert">{error}</p>}
      {!loading && !error && faculty.length === 0 && (
        <div className="sys-card text-center">
          <p>No faculty yet.</p>
          <Link href="/admin/faculty/new" className="btn-secondary mt-4 inline-flex no-underline">
            Create Faculty
          </Link>
        </div>
      )}
      {!loading && !error && faculty.length > 0 && (
        <div className="sys-card !max-w-none overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Name</th>
                <th>Email</th>
                <th>Employee Code</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {faculty.map((f) => (
                <tr key={f.id} className="border-b">
                  <td>{f.name}</td>
                  <td>{f.email || f.institutional_email || "—"}</td>
                  <td>{f.employee_code || "—"}</td>
                  <td>{f.is_active ? f.account_status.replaceAll("_", " ") : "ACADEMICALLY INACTIVE"}</td>
                  <td className="space-x-2 py-2">
                    <button type="button" className="btn-secondary" onClick={() => router.push(`/admin/faculty/${f.id}`)}>
                      View
                    </button>
                    <button type="button" className="btn-primary" onClick={() => router.push(`/admin/faculty/${f.id}/edit`)}>
                      Edit
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => toggleActive(f)}>
                      {f.is_active ? "Deactivate" : "Activate"}
                    </button>
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
