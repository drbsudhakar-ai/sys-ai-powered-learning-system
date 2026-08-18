import { useEffect, useState } from "react";
import Link from "next/link";
import AdminShell from "../../components/admin/AdminShell";
import BrandedState from "../../components/admin/BrandedState";
import useAdminAccess from "../../components/admin/useAdminAccess";
import {
  createNotificationRecipient,
  getApiErrorMessage,
  getInboxUnreadCount,
  listNotificationRecipients,
  listNotifications,
  retryNotification,
  updateNotificationRecipient,
} from "../../src/api";

const EVENTS = [
  "ASSESSMENT_PUBLISHED",
  "ASSESSMENT_COMPLETED",
  "RESULTS_PUBLISHED",
  "REPORT_GENERATED",
  "REPORT_CARD_GENERATED",
];

export default function NotificationsAdminPage() {
  const access = useAdminAccess();
  const [recipients, setRecipients] = useState([]);
  const [notes, setNotes] = useState([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    designation: "",
    email: "",
    recipient_type: "HIGHER_OFFICIAL",
    frequency: "IMMEDIATE",
    event_types: ["ASSESSMENT_PUBLISHED", "REPORT_CARD_GENERATED"],
  });

  const load = async () => {
    const [r, n, c] = await Promise.all([
      listNotificationRecipients(),
      listNotifications(),
      getInboxUnreadCount(),
    ]);
    setRecipients(r.data || []);
    setNotes(n.data || []);
    setUnread(c.data?.unread || 0);
  };

  useEffect(() => {
    if (access.status !== "ready") return;
    load().catch((err) => setError(getApiErrorMessage(err)));
  }, [access.status]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await createNotificationRecipient(form);
      setForm({
        name: "",
        designation: "",
        email: "",
        recipient_type: "HIGHER_OFFICIAL",
        frequency: "IMMEDIATE",
        event_types: ["ASSESSMENT_PUBLISHED", "REPORT_CARD_GENERATED"],
      });
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  if (access.status === "checking") {
    return <BrandedState title="Loading notification administration" message="Verifying administrator access and preparing notification configuration." />;
  }

  if (access.status !== "ready") {
    return <BrandedState type="error" title="Notification administration unavailable" message={access.error || "Administrator access could not be verified."} actionHref="/admin-dashboard" actionLabel="Back to Operations Overview" />;
  }

  return (
    <AdminShell
      user={access.user}
      unreadNotifications={unread}
      pageTitle="Notification Configuration"
      breadcrumb="Communication & Reports"
      scopeLabel={access.user?.role === "super_admin" ? "Platform-wide" : access.user?.college || "Institution scope"}
    >
      <div className="mx-auto w-full max-w-6xl px-4 py-8">
      <p className="sys-tagline !text-left !text-base">Admin</p>
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Notification Configuration</h1>
      {error && <p className="sys-card mt-4 text-red-600" role="alert">{error}</p>}

      <form onSubmit={onSubmit} className="sys-card mt-6 space-y-3 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Add Recipient</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-semibold">Name</label>
            <input id="name" className="input-field" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label htmlFor="designation" className="mb-1 block text-sm font-semibold">Designation</label>
            <input id="designation" className="input-field" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
          </div>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-semibold">Email</label>
            <input id="email" type="email" className="input-field" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label htmlFor="recipient_type" className="mb-1 block text-sm font-semibold">Type</label>
            <select id="recipient_type" className="input-field" value={form.recipient_type} onChange={(e) => setForm({ ...form, recipient_type: e.target.value })}>
              <option value="SYSTEM_ADMIN">SYSTEM_ADMIN</option>
              <option value="COURSE_COORDINATOR">COURSE_COORDINATOR</option>
              <option value="HIGHER_OFFICIAL">HIGHER_OFFICIAL</option>
              <option value="CUSTOM_RECIPIENT">CUSTOM_RECIPIENT</option>
            </select>
          </div>
        </div>
        <fieldset>
          <legend className="text-sm font-semibold">Events</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {EVENTS.map((ev) => (
              <label key={ev} className="text-sm">
                <input
                  type="checkbox"
                  className="mr-1"
                  checked={form.event_types.includes(ev)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...form.event_types, ev]
                      : form.event_types.filter((x) => x !== ev);
                    setForm({ ...form, event_types: next });
                  }}
                />
                {ev}
              </label>
            ))}
          </div>
        </fieldset>
        <button type="submit" className="btn-primary">Add Recipient</button>
      </form>

      <section className="sys-card mt-6 !max-w-none overflow-x-auto">
        <h2 className="font-bold text-[var(--sys-blue)]">Recipients</h2>
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th>Name</th>
              <th>Email</th>
              <th>Type</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {recipients.map((r) => (
              <tr key={r.id} className="border-b">
                <td>{r.name}</td>
                <td>{r.email}</td>
                <td>{r.recipient_type}</td>
                <td>{r.is_active ? "Yes" : "No"}</td>
                <td>
                  <button
                    type="button"
                    className="btn-secondary !px-2 !py-1 text-xs"
                    onClick={async () => {
                      await updateNotificationRecipient(r.id, { is_active: !r.is_active });
                      await load();
                    }}
                  >
                    {r.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="sys-card mt-6 !max-w-none overflow-x-auto">
        <h2 className="font-bold text-[var(--sys-blue)]">Notification Audit</h2>
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th>ID</th>
              <th>Event</th>
              <th>Status</th>
              <th>Retries</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {notes.map((n) => (
              <tr key={n.id} className="border-b">
                <td>{n.id}</td>
                <td>{n.event}</td>
                <td>{n.status}{n.failure_reason ? ` (${n.failure_reason})` : ""}</td>
                <td>{n.retry_count}</td>
                <td>
                  {(n.status === "FAILED" || n.status === "RETRYING") && (
                    <button
                      type="button"
                      className="btn-secondary !px-2 !py-1 text-xs"
                      onClick={async () => {
                        await retryNotification(n.id);
                        await load();
                      }}
                    >
                      Retry
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <p className="mt-6 text-sm">
        <Link href="/admin-dashboard" className="text-[var(--sys-blue)] no-underline hover:underline">← Admin Dashboard</Link>
      </p>
      </div>
    </AdminShell>
  );
}

NotificationsAdminPage.getLayout = (page) => page;
