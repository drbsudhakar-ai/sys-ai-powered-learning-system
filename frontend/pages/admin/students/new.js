import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { adminCreateStudent, getApiErrorMessage, getMe } from "../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../src/auth";

export default function NewStudentPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", mobile_number: "", roll_number: "", college: "", admission_year: "", present_year: "", academic_status: "ACTIVE" });
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
    if (!form.name.trim() || !form.roll_number.trim() || (!form.email.trim() && !form.mobile_number.trim())) {
      setError("Name, roll number, and at least one institutional contact are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminCreateStudent({
        name: form.name.trim(),
        email: form.email.trim() || null,
        mobile_number: form.mobile_number.trim() || null,
        roll_number: form.roll_number.trim(),
        college: form.college.trim() || null,
        admission_year: form.admission_year ? Number(form.admission_year) : null,
        present_year: form.present_year ? Number(form.present_year) : null,
        academic_status: form.academic_status,
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
        <p className="text-sm text-slate-600">This creates a pending institutional record. The student sets verified contacts and a password through controlled registration.</p>
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
          <label htmlFor="roll_number" className="mb-1 block text-sm font-semibold">Roll Number *</label>
          <input id="roll_number" name="roll_number" className="input-field" value={form.roll_number} onChange={onChange} required />
        </div>
        <div><label htmlFor="college" className="mb-1 block text-sm font-semibold">College</label><input id="college" name="college" className="input-field" value={form.college} onChange={onChange} /></div>
        <div><label htmlFor="admission_year" className="mb-1 block text-sm font-semibold">Admission Year</label><input id="admission_year" name="admission_year" type="number" min="1900" max="2200" className="input-field" value={form.admission_year} onChange={onChange} /></div>
        <div><label htmlFor="present_year" className="mb-1 block text-sm font-semibold">Present Year</label><input id="present_year" name="present_year" type="number" min="1" max="20" className="input-field" value={form.present_year} onChange={onChange} /></div>
        <div><label htmlFor="academic_status" className="mb-1 block text-sm font-semibold">Academic Status</label><select id="academic_status" name="academic_status" className="input-field" value={form.academic_status} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create Student"}
        </button>
      </form>
    </div>
  );
}
