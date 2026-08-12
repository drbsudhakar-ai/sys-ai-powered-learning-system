import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import {
  getInbox,
  getInboxUnreadCount,
  markInboxAllRead,
  markInboxRead,
} from "../src/api";
import { getToken } from "../src/auth";

export default function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const box = useRef(null);

  const refresh = async () => {
    if (!getToken()) return;
    try {
      const [c, list] = await Promise.all([getInboxUnreadCount(), getInbox({ unread_only: false })]);
      setUnread(c.data?.unread || 0);
      setItems(list.data || []);
    } catch {
      /* ignore when logged out */
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const onDoc = (e) => {
      if (box.current && !box.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const openItem = async (item) => {
    try {
      if (!item.is_read) await markInboxRead(item.delivery_id);
    } catch {
      /* ignore */
    }
    setOpen(false);
    await refresh();
    if (item.link_path) router.push(item.link_path);
  };

  if (!getToken()) return null;

  return (
    <div className="relative ml-2" ref={box}>
      <button
        type="button"
        aria-label="Notifications"
        className="relative rounded-xl px-3 py-2 text-sm font-semibold text-purple-100/80 transition hover:bg-white/10 hover:text-white"
        onClick={() => {
          setOpen((v) => !v);
          refresh();
        }}
      >
        Bell
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 rounded-full bg-[var(--sys-red,#c0392b)] px-1.5 text-[10px] text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-white/15 bg-[#120a2e] p-3 shadow-xl">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-bold text-white">Notifications</p>
            <button
              type="button"
              className="text-xs text-purple-200/80 hover:underline"
              onClick={async () => {
                await markInboxAllRead();
                refresh();
              }}
            >
              Mark all read
            </button>
          </div>
          <ul className="max-h-80 space-y-2 overflow-y-auto">
            {!items.length && <li className="text-xs text-purple-200/60">No notifications</li>}
            {items.slice(0, 12).map((n) => (
              <li key={n.delivery_id}>
                <button
                  type="button"
                  className={`w-full rounded-lg px-2 py-2 text-left text-xs ${
                    n.is_read ? "bg-white/5 text-purple-100/70" : "bg-white/10 text-white"
                  }`}
                  onClick={() => openItem(n)}
                >
                  <span className="font-semibold">{n.title || n.event}</span>
                  <span className="mt-0.5 block line-clamp-2 opacity-80">{n.message}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-right text-xs">
            <Link href="/notifications" className="text-purple-200 hover:underline" onClick={() => setOpen(false)}>
              View all / Preferences
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
