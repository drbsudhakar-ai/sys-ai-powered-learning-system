import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { adminGetStudent, adminUpdateStudent, getApiErrorMessage, getMe } from "../../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../../src/auth";

export default function EditStudentPage() {
  const router = useRouter();
  const { id } = router.query;
  const [form, setForm] = useState({ name: "", email: "", mobile_number: "", roll_number: "", college: "", admission_year: "", present_year: "", academic_status: "ACTIVE", password: "" });
  const [accountStatus, setAccountStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

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
        setAccountStatus(res.data.account_status || "");
        setForm({
          name: res.data.name || "",
          email: res.data.institutional_email || res.data.email || "",
          mobile_number: res.data.institutional_mobile || res.data.mobile_number || "",
          roll_number: res.data.roll_number || "",
          college: res.data.college || "",
          admission_year: res.data.admission_year || "",
          present_year: res.data.present_year || "",
          academic_status: res.data.academic_status || "ACTIVE",
          password: "",
        });
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

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim(),
        mobile_number: form.mobile_number.trim() || null,
        roll_number: form.roll_number.trim() || null,
        college: form.college.trim() || null,
        admission_year: form.admission_year ? Number(form.admission_year) : null,
        present_year: form.present_year ? Number(form.present_year) : null,
        academic_status: form.academic_status,
      };
      if (form.password) payload.password = form.password;
      await adminUpdateStudent(id, payload);
      router.push(`/admin/students/${id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to update student."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href={`/admin/students/${id || ""}`} className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Edit Student</h1>
      {loading && <p className="sys-card mt-6">Loading…</p>}
      {!loading && (
        <form onSubmit={onSubmit} className="sys-card mt-6 space-y-4 !max-w-none">
          {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-semibold">Name</label>
            <input id="name" name="name" className="input-field" value={form.name} onChange={onChange} required />
          </div>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-semibold">Institutional Email</label>
            <input id="email" name="email" type="email" className="input-field" value={form.email} onChange={onChange} required />
          </div>
          <div>
            <label htmlFor="mobile_number" className="mb-1 block text-sm font-semibold">Institutional Mobile (E.164)</label>
            <input id="mobile_number" name="mobile_number" type="tel" className="input-field" placeholder="+919876543210" value={form.mobile_number} onChange={onChange} />
          </div>
          <div>
            <label htmlFor="roll_number" className="mb-1 block text-sm font-semibold">Roll Number</label>
            <input id="roll_number" name="roll_number" className="input-field" value={form.roll_number} onChange={onChange} />
          </div>
          <div><label htmlFor="college" className="mb-1 block text-sm font-semibold">College</label><input id="college" name="college" className="input-field" value={form.college} onChange={onChange} /></div>
          <div><label htmlFor="admission_year" className="mb-1 block text-sm font-semibold">Admission Year</label><input id="admission_year" name="admission_year" type="number" min="1900" max="2200" className="input-field" value={form.admission_year} onChange={onChange} /></div>
          <div><label htmlFor="present_year" className="mb-1 block text-sm font-semibold">Present Year</label><input id="present_year" name="present_year" type="number" min="1" max="20" className="input-field" value={form.present_year} onChange={onChange} /></div>
          <div><label htmlFor="academic_status" className="mb-1 block text-sm font-semibold">Academic Status</label><select id="academic_status" name="academic_status" className="input-field" value={form.academic_status} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></div>
          {accountStatus === "ACTIVE" && (
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-semibold">New Password (optional)</label>
              <input id="password" name="password" type="password" className="input-field" value={form.password} onChange={onChange} minLength={8} autoComplete="new-password" />
            </div>
          )}
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Saving…" : "Save Changes"}
          </button>
        </form>
      )}
    </div>
  );
}
