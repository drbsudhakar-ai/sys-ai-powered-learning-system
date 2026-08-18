import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApiErrorMessage,
  getInbox,
  getInboxUnreadCount,
  getMe,
  getNotificationPreferences,
  markInboxAllRead,
  markInboxRead,
  updateNotificationPreferences,
} from "../src/api";
import { clearSession, getToken, isAdminRole, redirectToLogin, roleDisplayLabel } from "../src/auth";
import Layout from "../components/Layout";
import AdminShell from "../components/admin/AdminShell";
import BrandedState from "../components/admin/BrandedState";

export default function NotificationsPage() {
  const [user, setUser] = useState(null);
  const [sessionStatus, setSessionStatus] = useState("checking");
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const [prefs, setPrefs] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [inbox, p, count] = await Promise.all([
        getInbox({ unread_only: false }),
        getNotificationPreferences(),
        getInboxUnreadCount(),
      ]);
      setItems(inbox.data || []);
      setPrefs(p.data || []);
      setUnread(count.data?.unread || 0);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
      } else {
        setError(getApiErrorMessage(err));
      }
    }
  };

  useEffect(() => {
    let active = true;

    async function authorize() {
      if (!getToken()) {
        redirectToLogin();
        return;
      }
      try {
        const response = await getMe();
        if (!active) return;
        setUser(response.data);
        setSessionStatus("ready");
      } catch (err) {
        if (!active) return;
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setSessionStatus("error");
        setError(getApiErrorMessage(err));
      }
    }

    authorize();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (sessionStatus !== "ready") return;
    load();
  }, [sessionStatus]);

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

  const content = (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="sys-tagline !text-left !text-base">{roleDisplayLabel(user?.role)}</p>
          <h1 className="text-2xl font-bold text-[var(--sys-blue)]">Notifications</h1>
          <p className="mt-1 text-sm text-[var(--sys-gray)]">
            Your personal in-app notifications and delivery preferences.
          </p>
        </div>
        <Link href={isAdminRole(user?.role) ? "/admin-dashboard" : "/dashboard"} className="btn-secondary no-underline">
          ← Back to Dashboard
        </Link>
      </div>

      {error && <p className="sys-card mt-4 text-red-600" role="alert">{error}</p>}

      <div className="mt-4 flex gap-2">
        <button type="button" className="btn-secondary" onClick={load}>Refresh</button>
        <button
          type="button"
          className="btn-primary"
          onClick={async () => {
            await markInboxAllRead();
            await load();
          }}
          disabled={!unread}
        >
          Mark all read{unread ? ` (${unread})` : ""}
        </button>
      </div>

      <section className="sys-card mt-4 !max-w-none">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-bold text-[var(--sys-blue)]">Inbox</h2>
          <span className="text-xs font-semibold text-[var(--sys-gray)]">{unread} unread</span>
        </div>
        <ul className="mt-3 space-y-3">
          {items.map((n) => (
            <li key={n.delivery_id} className={`border-b pb-2 text-sm ${n.is_read ? "opacity-70" : ""}`}>
              <p className="font-semibold">{n.title || n.event}</p>
              <p className="text-[var(--sys-gray)]">{n.message}</p>
              <div className="mt-1 flex gap-2">
                {!n.is_read && (
                  <button type="button" className="btn-secondary !py-1 !px-2 text-xs" onClick={async () => { await markInboxRead(n.delivery_id); await load(); }}>
                    Mark read
                  </button>
                )}
                {n.link_path && (
                  <Link href={n.link_path} className="btn-secondary !py-1 !px-2 text-xs no-underline">Open</Link>
                )}
              </div>
            </li>
          ))}
          {!items.length && <li className="text-sm text-[var(--sys-gray)]">No notifications.</li>}
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

  if (sessionStatus === "checking") {
    return <BrandedState title="Loading notifications" message="Verifying your SYS session and preparing your notification workspace." />;
  }

  if (sessionStatus === "error") {
    return <BrandedState type="error" title="Notifications unavailable" message={error || "SYS could not verify your account."} actionHref="/dashboard" actionLabel="Back to dashboard" />;
  }

  if (isAdminRole(user?.role)) {
    return (
      <AdminShell
        user={user}
        unreadNotifications={unread}
        pageTitle="Notifications"
        breadcrumb="Administration"
        scopeLabel={user?.role === "super_admin" ? "Platform-wide" : user?.college || "Institution scope"}
      >
        {content}
      </AdminShell>
    );
  }

  return <Layout>{content}</Layout>;
}

NotificationsPage.getLayout = (page) => page;
