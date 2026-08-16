import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { adminGetFaculty, adminUpdateFaculty, getApiErrorMessage, getMe } from "../../../../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin } from "../../../../src/auth";

export default function EditFacultyPage() {
  const router = useRouter();
  const { id } = router.query;
  const [form, setForm] = useState({ name: "", email: "", mobile_number: "", employee_code: "", password: "" });
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
        const res = await adminGetFaculty(id);
        const f = res.data.faculty;
        setAccountStatus(f.account_status || "");
        setForm({
          name: f.name || "",
          email: f.institutional_email || f.email || "",
          mobile_number: f.institutional_mobile || f.mobile_number || "",
          employee_code: f.employee_code || "",
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
        employee_code: form.employee_code.trim() || null,
      };
      if (form.password) payload.password = form.password;
      await adminUpdateFaculty(id, payload);
      router.push(`/admin/faculty/${id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to update faculty."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8">
      <Link href={`/admin/faculty/${id || ""}`} className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Edit Faculty</h1>
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
            <label htmlFor="employee_code" className="mb-1 block text-sm font-semibold">Employee Code</label>
            <input id="employee_code" name="employee_code" className="input-field" value={form.employee_code} onChange={onChange} />
          </div>
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
