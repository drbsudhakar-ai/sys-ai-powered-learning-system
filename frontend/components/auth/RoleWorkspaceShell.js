import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useRef, useState } from "react";
import {
  AcademicCapIcon,
  BellIcon,
  BookOpenIcon,
  ChartBarIcon,
  ClipboardDocumentCheckIcon,
  HomeIcon,
  IdentificationIcon,
  PresentationChartLineIcon,
  UserGroupIcon,
  XMarkIcon,
  Bars3Icon,
  ChevronDownIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { clearSession, roleDisplayLabel } from "../../src/auth";
import { getInboxUnreadCount, getRoleDashboard } from "../../src/api";
import styles from "./RoleWorkspaceShell.module.css";

const STUDENT_ITEMS = [
  ["Dashboard", "/student-dashboard", HomeIcon],
  ["My profile", "/account/profile", IdentificationIcon],
  ["My courses", "/courses", AcademicCapIcon],
  ["Learning sessions", "/learning-sessions", BookOpenIcon],
  ["Assessments", "/assessments", ClipboardDocumentCheckIcon],
  ["Performance", "/my-performance", ChartBarIcon],
  ["Remedial learning", "/remedial/me", PresentationChartLineIcon],
  ["Notifications", "/notifications", BellIcon],
];

const FACULTY_ITEMS = [
  ["Dashboard", "/faculty-dashboard", HomeIcon],
  ["My profile", "/account/profile", IdentificationIcon],
  ["__ASSIGNED__", "", AcademicCapIcon],
  ["Learning sessions", "/learning-sessions", BookOpenIcon],
  ["Assessments", "/assessments", ClipboardDocumentCheckIcon],
  ["Student learning", "/performance", UserGroupIcon],
  ["Academic content reviews", "/faculty/academic-reviews", ClipboardDocumentCheckIcon],
  ["Academic reports", "/analytics", ChartBarIcon],
  ["Notifications", "/notifications", BellIcon],
];

function initials(name) {
  const parts = String(name || "SYS")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  return (
    parts.length > 1 ? `${parts[0][0]}${parts.at(-1)[0]}` : parts[0].slice(0, 2)
  ).toUpperCase();
}

export default function RoleWorkspaceShell({ role, identity, children }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [assignmentsOpen, setAssignmentsOpen] = useState(true);
  const [responsibilities, setResponsibilities] = useState({
    coordinator: false,
    expert: false,
  });
  const items = role === "faculty" ? FACULTY_ITEMS : STUDENT_ITEMS;
  const photo = identity?.photo_url || null;
  const profileMenuRef = useRef(null);
  const pageTitle =
    router.pathname === "/faculty-dashboard"
      ? "Dashboard"
      : router.pathname === "/faculty/coordinator-courses"
        ? "Coordinator Courses"
        : router.pathname === "/faculty/subject-expert-courses"
          ? "Subject Expert Courses"
          : router.pathname.includes("/workspace")
            ? "Course Workspace"
            : "Academic Workspace";

  useEffect(() => {
    if (role !== "faculty") return;
    let active = true;
    getRoleDashboard()
      .then(({ data }) => {
        if (active)
          setResponsibilities({
            coordinator: Boolean(data?.courses?.length),
            expert: Boolean(data?.subjects?.length),
          });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [role]);

  useEffect(() => {
    let active = true;
    getInboxUnreadCount()
      .then(({ data }) => {
        if (active) setUnread(Number(data?.unread ?? data?.count ?? 0));
      })
      .catch(() => {});
    const close = (event) => {
      if (!profileMenuRef.current?.contains(event.target))
        setProfileOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => {
      active = false;
      document.removeEventListener("mousedown", close);
    };
  }, []);

  const logout = () => {
    clearSession();
    router.replace("/login");
  };

  return (
    <div className={styles.workspace}>
      <button
        className={styles.mobileToggle}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label="Toggle workspace navigation"
      >
        {open ? <XMarkIcon /> : <Bars3Icon />} Menu
      </button>
      <aside className={`${styles.sidebar} ${open ? styles.sidebarOpen : ""}`}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>
            <Image
              src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
              alt=""
              width={42}
              height={42}
            />
          </span>
          <span className={styles.brandCopy}>
            <strong>SYS — Strengthen Your Skills</strong>
            <small>AI-Powered Learning Platform</small>
          </span>
        </div>
        <div className={styles.person}>
          <span className={styles.avatar}>
            {photo ? (
              <img
                src={photo}
                alt={`${identity?.name || "SYS user"} profile`}
              />
            ) : (
              initials(identity?.name)
            )}
          </span>
          <div>
            <strong>{identity?.name || "SYS User"}</strong>
            <small>{roleDisplayLabel(role)}</small>
          </div>
        </div>
        <p className={styles.sectionLabel}>
          {role === "faculty" ? "FACULTY WORKSPACE" : "STUDENT WORKSPACE"}
        </p>
        <nav aria-label={`${roleDisplayLabel(role)} workspace`}>
          {items.map(([label, href, Icon]) => {
            if (label === "__ASSIGNED__")
              return role === "faculty" &&
                (responsibilities.coordinator || responsibilities.expert) ? (
                <div className={styles.navGroup} key="assigned-courses">
                  <button
                    type="button"
                    className={styles.navGroupButton}
                    aria-expanded={assignmentsOpen}
                    onClick={() => setAssignmentsOpen((value) => !value)}
                  >
                    <AcademicCapIcon />
                    <span>Assigned Courses</span>
                    {assignmentsOpen ? (
                      <ChevronDownIcon />
                    ) : (
                      <ChevronRightIcon />
                    )}
                  </button>
                  {assignmentsOpen && (
                    <div className={styles.navChildren}>
                      {responsibilities.coordinator && (
                        <Link
                          href="/faculty/coordinator-courses"
                          className={
                            router.pathname === "/faculty/coordinator-courses"
                              ? styles.active
                              : ""
                          }
                          onClick={() => setOpen(false)}
                        >
                          Coordinator Courses
                        </Link>
                      )}
                      {responsibilities.expert && (
                        <Link
                          href="/faculty/subject-expert-courses"
                          className={
                            router.pathname ===
                            "/faculty/subject-expert-courses"
                              ? styles.active
                              : ""
                          }
                          onClick={() => setOpen(false)}
                        >
                          Subject Expert Courses
                        </Link>
                      )}
                    </div>
                  )}
                </div>
              ) : null;
            const routeHref = href.split("#")[0];
            const active =
              router.pathname === routeHref ||
              (routeHref !== "/courses" &&
                router.pathname.startsWith(`${routeHref}/`));
            return (
              <Link
                key={href}
                href={href}
                className={active ? styles.active : ""}
                onClick={() => setOpen(false)}
              >
                <Icon />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className={styles.sidebarFooter}>
          <strong>SYS — Strengthen Your Skills</strong>
          <span>Shape Your Successful Future.</span>
          <small>Conceived and developed by Dr. Sudhakar Bolleddu</small>
        </div>
      </aside>
      <div className={styles.content}>
        <header className={styles.topbar}>
          <div className={styles.topbarContext}>
            <strong>
              {role === "faculty" ? "Faculty Workspace" : "Student Workspace"}
            </strong>
            <span aria-hidden="true">/</span>
            <b>{pageTitle}</b>
          </div>
          <div className={styles.topbarActions}>
            <Link
              href="/notifications"
              className={styles.notificationButton}
              aria-label={`${unread} unread notifications`}
            >
              <BellIcon aria-hidden="true" />
              {unread > 0 && <span>{unread > 99 ? "99+" : unread}</span>}
            </Link>
            <div className={styles.profileMenu} ref={profileMenuRef}>
              <button
                type="button"
                className={styles.profileButton}
                aria-expanded={profileOpen}
                onClick={() => setProfileOpen((value) => !value)}
              >
                <span className={styles.topbarAvatar}>
                  {photo ? (
                    <img src={photo} alt="" />
                  ) : (
                    initials(identity?.name)
                  )}
                </span>
                <span className={styles.profileCopy}>
                  <strong>{identity?.name || "SYS User"}</strong>
                  <small>{roleDisplayLabel(role)}</small>
                </span>
                <ChevronDownIcon aria-hidden="true" />
              </button>
              {profileOpen && (
                <div className={styles.profilePopover}>
                  <Link href="/account/profile">View profile</Link>
                  <button type="button" onClick={logout}>
                    Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
