import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  AcademicCapIcon,
  AdjustmentsHorizontalIcon,
  Bars3Icon,
  BellIcon,
  BookOpenIcon,
  ChartBarSquareIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  ClipboardDocumentCheckIcon,
  DocumentChartBarIcon,
  HomeIcon,
  PresentationChartLineIcon,
  UserGroupIcon,
  UsersIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { clearSession } from "../../src/auth";
import styles from "./AdminDashboard.module.css";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/admin-dashboard", icon: HomeIcon }],
  },
  {
    label: "People",
    items: [
      { label: "Students", href: "/admin/students", icon: UsersIcon },
      { label: "Faculty", href: "/admin/faculty", icon: UserGroupIcon },
    ],
  },
  {
    label: "Academic setup",
    items: [
      { label: "Programmes", href: "/courses", icon: AcademicCapIcon },
      { label: "Responsibilities", href: "/admin/faculty", icon: AdjustmentsHorizontalIcon },
    ],
  },
  {
    label: "Learning operations",
    items: [
      { label: "Learning sessions", href: "/learning-sessions", icon: BookOpenIcon },
      { label: "Assessments", href: "/assessments", icon: ClipboardDocumentCheckIcon },
      { label: "Learning intelligence", href: "/analytics/admin", icon: ChartBarSquareIcon },
      { label: "Learning journeys", href: "/learning-journey/admin", icon: PresentationChartLineIcon },
      { label: "Notifications", href: "/admin/notifications", icon: BellIcon },
      { label: "Reports", href: "/performance", icon: DocumentChartBarIcon },
    ],
  },
];

function initials(name) {
  return (name || "SYS Admin")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function AdminShell({ user, notificationFailures, children }) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!drawerOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [drawerOpen]);

  function isActive(href) {
    return router.pathname === href || (href !== "/admin-dashboard" && router.pathname.startsWith(`${href}/`));
  }

  async function logout() {
    clearSession();
    await router.replace("/login?reason=signed-out");
  }

  return (
    <div className={`${styles.adminShell} ${collapsed ? styles.shellCollapsed : ""}`}>
      <aside
        id="admin-navigation"
        className={`${styles.sidebar} ${drawerOpen ? styles.drawerOpen : ""}`}
        aria-label="Administrator navigation"
      >
        <div className={styles.sidebarBrand}>
          <Link href="/admin-dashboard" aria-label="SYS administrator dashboard" onClick={() => setDrawerOpen(false)}>
            <Image
              src={collapsed
                ? "/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
                : "/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"}
              alt="SYS – Strengthen Your Skills"
              width={collapsed ? 160 : 520}
              height={collapsed ? 160 : 144}
              className={collapsed ? styles.compactLogo : styles.sidebarLogo}
              preload
            />
          </Link>
          <button
            className={styles.drawerClose}
            type="button"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close administrator navigation"
          >
            <XMarkIcon aria-hidden="true" />
          </button>
        </div>

        <nav className={styles.sidebarNav}>
          {NAV_GROUPS.map((group) => (
            <div className={styles.navGroup} key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={`${group.label}-${item.href}`}
                    href={item.href}
                    className={isActive(item.href) ? styles.navActive : ""}
                    aria-current={isActive(item.href) ? "page" : undefined}
                    title={collapsed ? item.label : undefined}
                    onClick={() => setDrawerOpen(false)}
                  >
                    <Icon aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className={styles.sidebarFoot}>
          <button
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronDoubleRightIcon aria-hidden="true" /> : <ChevronDoubleLeftIcon aria-hidden="true" />}
            <span>Collapse menu</span>
          </button>
        </div>
      </aside>

      {drawerOpen && (
        <button
          type="button"
          className={styles.scrim}
          aria-label="Close administrator navigation"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <div className={styles.topbarContext}>
            <button
              type="button"
              className={styles.mobileMenu}
              onClick={() => setDrawerOpen(true)}
              aria-label="Open administrator navigation"
              aria-controls="admin-navigation"
              aria-expanded={drawerOpen}
            >
              <Bars3Icon aria-hidden="true" />
            </button>
            <div>
              <p>Administration <span aria-hidden="true">/</span> Overview</p>
              <span>Institutional operations and readiness</span>
            </div>
          </div>

          <div className={styles.topbarActions}>
            <Link href="/admin/notifications" className={styles.notificationButton} aria-label={notificationFailures > 0 ? `${notificationFailures} failed notifications` : "Notifications"}>
              <BellIcon aria-hidden="true" />
              {notificationFailures > 0 && <span>{notificationFailures > 99 ? "99+" : notificationFailures}</span>}
            </Link>
            <div className={styles.profile}>
              <span className={styles.avatar} aria-hidden="true">{initials(user?.name)}</span>
              <span className={styles.profileCopy}>
                <strong>{user?.name || "Administrator"}</strong>
                <small>Administrator</small>
              </span>
            </div>
            <button className={styles.logoutButton} type="button" onClick={logout}>Log out</button>
          </div>
        </header>

        <main className={styles.adminMain}>{children}</main>
      </div>
    </div>
  );
}
