import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AcademicCapIcon,
  AdjustmentsHorizontalIcon,
  Bars3Icon,
  BellIcon,
  BookOpenIcon,
  ChartBarSquareIcon,
  ChevronDownIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  ClipboardDocumentCheckIcon,
  DocumentChartBarIcon,
  HomeIcon,
  PresentationChartLineIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  UsersIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { clearSession, roleDisplayLabel } from "../../src/auth";
import styles from "./AdminDashboard.module.css";

const NAV_GROUPS = [
  {
    label: "Overview",
    icon: HomeIcon,
    items: [{ label: "Operations overview", href: "/admin-dashboard", icon: HomeIcon }],
  },
  {
    label: "People & Access",
    icon: UsersIcon,
    items: [
      { label: "Student Master", href: "/admin/students", icon: UsersIcon },
      { label: "Faculty Master", href: "/admin/faculty", icon: UserGroupIcon },
    ],
  },
  {
    label: "Academic Management",
    icon: AcademicCapIcon,
    items: [
      { label: "Programmes", href: "/courses", icon: AcademicCapIcon },
      { label: "Academic responsibilities", href: "/admin/faculty", icon: AdjustmentsHorizontalIcon },
    ],
  },
  {
    label: "Learning & Assessment",
    icon: BookOpenIcon,
    items: [
      { label: "Learning sessions", href: "/learning-sessions", icon: BookOpenIcon },
      { label: "Assessments", href: "/assessments", icon: ClipboardDocumentCheckIcon },
      { label: "Question intelligence", href: "/question-bank", icon: QuestionMarkCircleIcon },
    ],
  },
  {
    label: "Intelligence & Student Support",
    icon: ChartBarSquareIcon,
    items: [
      { label: "Learning intelligence", href: "/analytics/admin", icon: ChartBarSquareIcon },
      { label: "Learning journeys", href: "/learning-journey/admin", icon: PresentationChartLineIcon },
      { label: "Remedial learning", href: "/remedial", icon: AdjustmentsHorizontalIcon },
    ],
  },
  {
    label: "Communication & Reports",
    icon: DocumentChartBarIcon,
    items: [
      { label: "Notifications", href: "/admin/notifications", icon: BellIcon },
      { label: "Performance reports", href: "/performance", icon: DocumentChartBarIcon },
    ],
  },
  {
    label: "System Administration",
    icon: ShieldCheckIcon,
    roles: ["super_admin"],
    items: [
      { label: "Security audit activity", href: "/admin-dashboard#system-administration", icon: ShieldCheckIcon },
    ],
  },
];

function initials(name) {
  return (name || "SYS")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function AdminShell({
  user,
  unreadNotifications = 0,
  pageTitle = "Overview",
  breadcrumb = "Administration",
  scopeLabel,
  children,
}) {
  const router = useRouter();
  const menuButtonRef = useRef(null);
  const profileButtonRef = useRef(null);
  const profileMenuRef = useRef(null);
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const allowedGroups = useMemo(
    () => NAV_GROUPS.filter((group) => !group.roles || group.roles.includes(user?.role)),
    [user?.role],
  );
  const activeGroup = useMemo(
    () => allowedGroups.find((group) => group.items.some((item) => {
      const itemPath = item.href.split("#")[0];
      return router.pathname === itemPath
      || (itemPath !== "/admin-dashboard" && router.pathname.startsWith(`${itemPath}/`));
    }))?.label || "Overview",
    [allowedGroups, router.pathname],
  );
  const [expandedGroup, setExpandedGroup] = useState(activeGroup);

  useEffect(() => {
    const stored = window.localStorage.getItem("sys-admin-sidebar-collapsed");
    setCollapsed(stored === "true");
  }, []);

  useEffect(() => {
    setExpandedGroup(activeGroup);
    if (drawerOpen) {
      setDrawerOpen(false);
      menuButtonRef.current?.focus();
    }
  }, [activeGroup]);

  useEffect(() => {
    if (!drawerOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [drawerOpen]);

  useEffect(() => {
    if (!profileOpen) return undefined;
    const close = (event) => {
      if (event.key === "Escape") {
        setProfileOpen(false);
        profileButtonRef.current?.focus();
      } else if (!profileMenuRef.current?.contains(event.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("keydown", close);
    document.addEventListener("pointerdown", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("pointerdown", close);
    };
  }, [profileOpen]);

  function isActive(href) {
    return router.pathname === href || (href !== "/admin-dashboard" && router.pathname.startsWith(`${href}/`));
  }

  function toggleCollapsed() {
    setCollapsed((value) => {
      window.localStorage.setItem("sys-admin-sidebar-collapsed", String(!value));
      return !value;
    });
  }

  function closeDrawer({ restoreFocus = true } = {}) {
    setDrawerOpen(false);
    if (restoreFocus) window.requestAnimationFrame(() => menuButtonRef.current?.focus());
  }

  async function logout() {
    clearSession();
    await router.replace("/login?reason=signed-out");
  }

  const currentYear = new Date().getFullYear();

  return (
    <div className={`${styles.adminShell} ${collapsed ? styles.shellCollapsed : ""}`}>
      <aside id="admin-navigation" className={`${styles.sidebar} ${drawerOpen ? styles.drawerOpen : ""}`} aria-label="Administrator navigation">
        <div className={styles.sidebarBrand}>
          <Link href="/admin-dashboard" aria-label="SYS administrator dashboard" onClick={() => closeDrawer({ restoreFocus: false })}>
            <Image
              src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
              alt="SYS — Strengthen Your Skills"
              width={520}
              height={144}
              className={styles.sidebarLogo}
              preload
            />
            <Image
              src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
              alt=""
              width={256}
              height={248}
              className={styles.compactLogo}
            />
          </Link>
          <button className={styles.drawerClose} type="button" onClick={() => closeDrawer()} aria-label="Close administrator navigation">
            <XMarkIcon aria-hidden="true" />
          </button>
        </div>

        <nav className={styles.sidebarNav} aria-label="Administrator modules">
          {allowedGroups.map((group, groupIndex) => {
            const GroupIcon = group.icon;
            const expanded = expandedGroup === group.label;
            const controlId = `admin-nav-group-${groupIndex}`;
            return (
              <div className={styles.navGroup} key={group.label}>
                <button type="button" className={styles.navGroupToggle} aria-expanded={expanded} aria-controls={controlId} onClick={() => setExpandedGroup(expanded ? "" : group.label)} title={collapsed ? group.label : undefined}>
                  <GroupIcon aria-hidden="true" />
                  <span>{group.label}</span>
                  <ChevronDownIcon aria-hidden="true" />
                </button>
                <div id={controlId} className={styles.navItems} hidden={!expanded}>
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link key={`${group.label}-${item.href}-${item.label}`} href={item.href} className={isActive(item.href) ? styles.navActive : ""} aria-current={isActive(item.href) ? "page" : undefined} title={collapsed ? item.label : undefined} onClick={() => closeDrawer({ restoreFocus: false })}>
                        <Icon aria-hidden="true" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        <div className={styles.sidebarFoot}>
          <div className={styles.sidebarIdentity}>
            <strong>SYS — Strengthen Your Skills</strong>
            <span>Shape Your Successful Future.</span>
            <small>© {currentYear} SYS</small>
          </div>
          <button type="button" onClick={toggleCollapsed} aria-expanded={!collapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <ChevronDoubleRightIcon aria-hidden="true" /> : <ChevronDoubleLeftIcon aria-hidden="true" />}
            <span>Collapse menu</span>
          </button>
        </div>
      </aside>

      {drawerOpen && <button type="button" className={styles.scrim} aria-label="Close administrator navigation" onClick={() => closeDrawer()} />}

      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <div className={styles.topbarContext}>
            <button ref={menuButtonRef} type="button" className={styles.mobileMenu} onClick={() => setDrawerOpen(true)} aria-label="Open administrator navigation" aria-controls="admin-navigation" aria-expanded={drawerOpen}>
              <Bars3Icon aria-hidden="true" />
            </button>
            <div>
              <p>{breadcrumb} <span aria-hidden="true">/</span> {pageTitle}</p>
              <span>{scopeLabel || "Institution scope unavailable"}</span>
            </div>
          </div>

          <div className={styles.topbarActions}>
            <Link href="/notifications" className={styles.notificationButton} aria-label={`${unreadNotifications} unread notifications`}>
              <BellIcon aria-hidden="true" />
              {unreadNotifications > 0 && <span>{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}
            </Link>
            <div className={styles.profileMenu} ref={profileMenuRef}>
              <button ref={profileButtonRef} type="button" className={styles.profile} aria-expanded={profileOpen} aria-controls="admin-profile-menu" onClick={() => setProfileOpen((value) => !value)}>
                <span className={styles.avatar} aria-hidden="true">{initials(user?.name)}</span>
                <span className={styles.profileCopy}>
                  <strong>{user?.name || "Administrator"}</strong>
                  <small>{roleDisplayLabel(user?.role)}</small>
                </span>
                <ChevronDownIcon aria-hidden="true" />
              </button>
              {profileOpen && (
                <div id="admin-profile-menu" className={styles.profilePopover}>
                  <strong>{user?.name || "Administrator"}</strong>
                  <span>{roleDisplayLabel(user?.role)}</span>
                  <button type="button" onClick={logout}>Log out</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className={styles.adminMain}>{children}</main>
      </div>
    </div>
  );
}
