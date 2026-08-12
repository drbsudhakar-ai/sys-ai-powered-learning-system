import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, getApiErrorMessage } from "../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../src/auth";

export default function AdminDashboardPage() {
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isAdminRole(me.data.role)) {
          setError("Admin access required.");
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err));
      } finally {
        setReady(true);
      }
    })();
  }, []);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Admin</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Admin Dashboard</h1>
      {!ready && <p className="sys-card mt-6">Loading…</p>}
      {ready && error && <p className="sys-card mt-6 text-red-600">{error}</p>}
      {ready && !error && (
        <div className="mt-6 grid gap-6 md:grid-cols-3">
          <section className="sys-card !max-w-none">
            <h2 className="text-lg font-bold text-[var(--sys-blue)]">Courses</h2>
            <p className="mt-2 text-sm text-[var(--sys-gray)]">Manage SYS courses.</p>
            <Link href="/courses" className="btn-primary mt-4 inline-flex no-underline">Open Courses</Link>
          </section>
          <section className="sys-card !max-w-none">
            <h2 className="text-lg font-bold text-[var(--sys-blue)]">Students</h2>
            <p className="mt-2 text-sm text-[var(--sys-gray)]">Create and manage student accounts.</p>
            <Link href="/admin/students" className="btn-primary mt-4 inline-flex no-underline">Manage Students</Link>
          </section>
          <section className="sys-card !max-w-none">
            <h2 className="text-lg font-bold text-[var(--sys-blue)]">Faculty</h2>
            <p className="mt-2 text-sm text-[var(--sys-gray)]">Manage faculty and academic responsibilities.</p>
            <Link href="/admin/faculty" className="btn-primary mt-4 inline-flex no-underline">Manage Faculty</Link>
          </section>
        </div>
      )}
    </div>
  );
}
