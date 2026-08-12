import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { adminCreateStudent, getApiErrorMessage, getMe } from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function NewStudentPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "", roll_number: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        const me = await getMe();
        if (!isAdminRole(me.data.role)) setError("Admin access required.");
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        }
      }
    })();
  }, []);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.name.trim() || !form.email.trim() || !form.password || !form.roll_number.trim()) {
      setError("Name, email, password, and roll number are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminCreateStudent({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        roll_number: form.roll_number.trim(),
      });
      router.push(`/admin/students/${res.data.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to create student."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/admin/students" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to students
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Create Student</h1>
      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-4 !max-w-none">
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-semibold">Name *</label>
          <input id="name" name="name" className="input-field" value={form.name} onChange={onChange} required />
        </div>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-semibold">Email *</label>
          <input id="email" name="email" type="email" className="input-field" value={form.email} onChange={onChange} required />
        </div>
        <div>
          <label htmlFor="roll_number" className="mb-1 block text-sm font-semibold">Roll Number *</label>
          <input id="roll_number" name="roll_number" className="input-field" value={form.roll_number} onChange={onChange} required />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-semibold">Temporary Password *</label>
          <input id="password" name="password" type="password" className="input-field" value={form.password} onChange={onChange} required minLength={6} />
        </div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create Student"}
        </button>
      </form>
    </div>
  );
}
