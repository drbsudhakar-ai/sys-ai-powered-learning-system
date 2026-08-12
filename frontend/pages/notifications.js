import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getInbox,
  getNotificationPreferences,
  markInboxAllRead,
  markInboxRead,
  updateNotificationPreferences,
} from "../src/api";
import { clearSession, getToken, redirectToLogin } from "../src/auth";

export default function NotificationsPage() {
  const [items, setItems] = useState([]);
  const [prefs, setPrefs] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [inbox, p] = await Promise.all([getInbox(), getNotificationPreferences()]);
      setItems(inbox.data || []);
      setPrefs(p.data || []);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
      } else setError(getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    if (!getToken()) return redirectToLogin();
    load();
  }, []);

  const togglePref = async (category, field) => {
    const next = prefs.map((p) =>
      p.category === category ? { ...p, [field]: !p[field] } : p
    );
    setPrefs(next);
    try {
      await updateNotificationPreferences(
        next.map((p) => ({
          category: p.category,
          email_enabled: p.email_enabled,
          in_app_enabled: p.in_app_enabled,
          sms_enabled: p.sms_enabled,
        }))
      );
    } catch (err) {
      setError(getApiErrorMessage(err));
      load();
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Notifications</h1>
      {error && <p className="sys-card mt-4 text-red-600">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button type="button" className="btn-secondary" onClick={load}>Refresh</button>
        <button
          type="button"
          className="btn-primary"
          onClick={async () => {
            await markInboxAllRead();
            load();
          }}
        >
          Mark all read
        </button>
      </div>

      <section className="sys-card mt-4 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Inbox</h2>
        <ul className="mt-3 space-y-3">
          {items.map((n) => (
            <li key={n.delivery_id} className={`border-b pb-2 text-sm ${n.is_read ? "opacity-70" : ""}`}>
              <p className="font-semibold">{n.title || n.event}</p>
              <p className="text-[var(--sys-gray)]">{n.message}</p>
              <div className="mt-1 flex gap-2">
                {!n.is_read && (
                  <button type="button" className="btn-secondary !py-1 !px-2 text-xs" onClick={async () => { await markInboxRead(n.delivery_id); load(); }}>
                    Mark read
                  </button>
                )}
                {n.link_path && (
                  <Link href={n.link_path} className="btn-secondary !py-1 !px-2 text-xs no-underline">Open</Link>
                )}
              </div>
            </li>
          ))}
          {!items.length && <li className="text-sm text-[var(--sys-gray)]">Empty</li>}
        </ul>
      </section>

      <section className="sys-card mt-4 !max-w-none">
        <h2 className="font-bold text-[var(--sys-blue)]">Preferences</h2>
        <p className="mt-1 text-xs text-[var(--sys-gray)]">SMS is reserved for future delivery.</p>
        <ul className="mt-3 space-y-3 text-sm">
          {prefs.map((p) => (
            <li key={p.category} className="flex flex-wrap items-center gap-4 border-b pb-2">
              <span className="w-48 font-semibold">{p.category}</span>
              <label><input type="checkbox" checked={!!p.email_enabled} onChange={() => togglePref(p.category, "email_enabled")} /> Email</label>
              <label><input type="checkbox" checked={!!p.in_app_enabled} onChange={() => togglePref(p.category, "in_app_enabled")} /> In-app</label>
              <label className="opacity-50"><input type="checkbox" checked={!!p.sms_enabled} disabled /> SMS (future)</label>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
