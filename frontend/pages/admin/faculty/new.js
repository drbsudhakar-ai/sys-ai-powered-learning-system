import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { adminCreateFaculty, getApiErrorMessage, getMe } from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function NewFacultyPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", mobile_number: "", employee_code: "", college: "", department: "", designation: "", employment_status: "ACTIVE" });
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
    if (!form.name.trim() || !form.employee_code.trim() || (!form.email.trim() && !form.mobile_number.trim())) {
      setError("Name, employee code, and at least one institutional contact are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminCreateFaculty({
        name: form.name.trim(),
        email: form.email.trim() || null,
        mobile_number: form.mobile_number.trim() || null,
        employee_code: form.employee_code.trim(),
        college: form.college.trim() || null,
        department: form.department.trim() || null,
        designation: form.designation.trim() || null,
        employment_status: form.employment_status,
      });
      router.push(`/admin/faculty/${res.data.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to create faculty."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href="/admin/faculty" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to faculty
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Create Faculty</h1>
      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-4 !max-w-none">
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <p className="text-sm text-slate-600">This creates a pending institutional record. The faculty member sets verified contacts and a password through controlled registration.</p>
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-semibold">Name *</label>
          <input id="name" name="name" className="input-field" value={form.name} onChange={onChange} required />
        </div>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-semibold">Institutional Email</label>
          <input id="email" name="email" type="email" className="input-field" value={form.email} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="mobile_number" className="mb-1 block text-sm font-semibold">Institutional Mobile (E.164)</label>
          <input id="mobile_number" name="mobile_number" type="tel" className="input-field" placeholder="+919876543210" value={form.mobile_number} onChange={onChange} />
        </div>
        <div>
          <label htmlFor="employee_code" className="mb-1 block text-sm font-semibold">Employee Code *</label>
          <input id="employee_code" name="employee_code" className="input-field" value={form.employee_code} onChange={onChange} required />
        </div>
        <div><label htmlFor="college" className="mb-1 block text-sm font-semibold">College</label><input id="college" name="college" className="input-field" value={form.college} onChange={onChange} /></div>
        <div><label htmlFor="department" className="mb-1 block text-sm font-semibold">Department</label><input id="department" name="department" className="input-field" value={form.department} onChange={onChange} /></div>
        <div><label htmlFor="designation" className="mb-1 block text-sm font-semibold">Designation</label><input id="designation" name="designation" className="input-field" value={form.designation} onChange={onChange} /></div>
        <div><label htmlFor="employment_status" className="mb-1 block text-sm font-semibold">Employment Status</label><select id="employment_status" name="employment_status" className="input-field" value={form.employment_status} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create Faculty"}
        </button>
      </form>
    </div>
  );
}
