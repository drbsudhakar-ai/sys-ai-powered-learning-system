import Head from "next/head";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import {
  AcademicCapIcon,
  ArrowPathIcon,
  BellAlertIcon,
  BookOpenIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  ClipboardDocumentCheckIcon,
  CloudArrowUpIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  UsersIcon,
  WrenchScrewdriverIcon,
  XCircleIcon,
} from "@heroicons/react/24/outline";
import AdminShell from "../components/admin/AdminShell";
import styles from "../components/admin/AdminDashboard.module.css";
import {
  adminListCourseCoordinators,
  adminListFaculty,
  adminListStudents,
  adminListSubjectExperts,
  adminListSubjects,
  getCourses,
  getMe,
  listNotifications,
} from "../src/api";
import { clearSession, getToken, isAdminRole, roleLandingPath } from "../src/auth";

const DATA_LOADERS = {
  students: adminListStudents,
  faculty: adminListFaculty,
  courses: getCourses,
  subjects: adminListSubjects,
  coordinators: adminListCourseCoordinators,
  experts: adminListSubjectExperts,
  notifications: listNotifications,
};

const isRecord = (value) => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const isInteger = (value) => Number.isInteger(value);
const isNullableString = (value) => value === null || typeof value === "string";

const COLLECTION_VALIDATORS = {
  students: (item) => isRecord(item)
    && isInteger(item.id)
    && typeof item.name === "string"
    && typeof item.email === "string"
    && typeof item.is_active === "boolean"
    && isNullableString(item.roll_number),
  faculty: (item) => isRecord(item)
    && isInteger(item.id)
    && typeof item.name === "string"
    && typeof item.email === "string"
    && typeof item.is_active === "boolean"
    && isNullableString(item.employee_code),
  courses: (item) => isRecord(item) && isInteger(item.id) && typeof item.is_active === "boolean",
  subjects: (item) => isRecord(item) && isInteger(item.id),
  coordinators: (item) => isRecord(item) && isInteger(item.course_id),
  experts: (item) => isRecord(item) && isInteger(item.subject_id),
  notifications: (item) => isRecord(item)
    && typeof item.status === "string"
    && isNullableString(item.failure_reason),
};

function isValidCollection(key, data) {
  const validateItem = COLLECTION_VALIDATORS[key];
  return Array.isArray(data) && Boolean(validateItem) && data.every(validateItem);
}

function sourceValue(sources, key) {
  return sources[key]?.available ? sources[key].data : null;
}

function MetricCard({ icon: Icon, label, value, note, available = true }) {
  return (
    <article className={styles.metricCard}>
      <span className={styles.metricIcon}><Icon aria-hidden="true" /></span>
      <div>
        <p>{label}</p>
        <strong>{available ? value : "Unavailable"}</strong>
        <span>{available ? note : "The source is unavailable or returned invalid data."}</span>
      </div>
    </article>
  );
}

function StatusPill({ status }) {
  const labels = { complete: "Complete", pending: "Needs attention", unavailable: "Unavailable" };
  const Icon = status === "complete" ? CheckCircleIcon : status === "pending" ? ExclamationTriangleIcon : InformationCircleIcon;
  return (
    <span className={`${styles.statusPill} ${styles[`status_${status}`]}`}>
      <Icon aria-hidden="true" /> {labels[status]}
    </span>
  );
}

function AttentionCard({ title, description, count, available, href, action }) {
  return (
    <article className={styles.attentionCard}>
      <div className={styles.attentionTop}>
        <span className={!available ? styles.neutralIssue : count > 0 ? styles.openIssue : styles.clearIssue}>
          {!available ? <InformationCircleIcon aria-hidden="true" /> : count > 0 ? <ExclamationTriangleIcon aria-hidden="true" /> : <CheckCircleIcon aria-hidden="true" />}
        </span>
        <strong>{available ? count : "—"}</strong>
      </div>
      <h3>{title}</h3>
      <p>{available ? description : "This check is unavailable because its source is unavailable or invalid."}</p>
      {href && <Link href={href}>{action}<ChevronRightIcon aria-hidden="true" /></Link>}
    </article>
  );
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [sources, setSources] = useState({});
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setPageError("");

      if (!getToken()) {
        await router.replace("/login?reason=unauthorized");
        return;
      }

      try {
        const { data: account } = await getMe();
        if (!active) return;
        if (!account.is_active) {
          clearSession();
          await router.replace("/login?reason=unauthorized");
          return;
        }
        if (!isAdminRole(account.role)) {
          await router.replace(roleLandingPath(account.role) || "/login?reason=unauthorized");
          return;
        }
        setUser(account);

        const entries = Object.entries(DATA_LOADERS);
        const results = await Promise.allSettled(entries.map(([, loader]) => loader()));
        if (!active) return;

        const rejectedStatus = (statusCode) => results.some(
          (result) => result.status === "rejected" && result.reason?.response?.status === statusCode,
        );
        if (rejectedStatus(401)) {
          setSources({});
          setUser(null);
          clearSession();
          await router.replace("/login?reason=expired");
          return;
        }
        if (rejectedStatus(403)) {
          setSources({});
          setUser(null);
          clearSession();
          await router.replace("/login?reason=unauthorized");
          return;
        }

        const nextSources = {};
        results.forEach((result, index) => {
          const key = entries[index][0];
          if (result.status === "fulfilled" && isValidCollection(key, result.value?.data)) {
            nextSources[key] = { available: true, data: result.value.data };
          } else {
            nextSources[key] = {
              available: false,
              data: null,
              reason: result.status === "fulfilled" ? "invalid-response" : "request-failed",
            };
          }
        });
        setSources(nextSources);
      } catch (error) {
        if (!active) return;
        if (error?.response?.status === 401) {
          clearSession();
          await router.replace("/login?reason=expired");
          return;
        }
        if (error?.response?.status === 403) {
          setSources({});
          setUser(null);
          clearSession();
          await router.replace("/login?reason=unauthorized");
          return;
        } else {
          setPageError("SYS could not verify the administrator account. Check the API service and try again.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [reloadKey, router]);

  const students = sourceValue(sources, "students");
  const faculty = sourceValue(sources, "faculty");
  const courses = sourceValue(sources, "courses");
  const subjects = sourceValue(sources, "subjects");
  const coordinators = sourceValue(sources, "coordinators");
  const experts = sourceValue(sources, "experts");
  const notifications = sourceValue(sources, "notifications");

  const activeStudents = students?.filter((item) => item.is_active).length;
  const activeFaculty = faculty?.filter((item) => item.is_active).length;
  const activeCourses = courses?.filter((item) => item.is_active).length;
  const coordinatorCourseIds = new Set((coordinators || []).map((item) => item.course_id));
  const coursesWithoutCoordinator = courses && coordinators
    ? courses.filter((course) => course.is_active && !coordinatorCourseIds.has(course.id)).length
    : null;
  const expertSubjectIds = new Set((experts || []).map((item) => item.subject_id));
  const subjectsWithoutExpert = subjects && experts ? subjects.filter((subject) => !expertSubjectIds.has(subject.id)).length : null;
  const incompleteStudents = students?.filter((item) => item.is_active && (!item.name || !item.email || !item.roll_number)).length;
  const incompleteFaculty = faculty?.filter((item) => item.is_active && (!item.name || !item.email || !item.employee_code)).length;
  const failedNotifications = notifications?.filter((item) => {
    const status = String(item.status || "").toUpperCase();
    return Boolean(item.failure_reason) || ["FAILED", "ERROR", "DEAD_LETTER"].includes(status);
  }).length;
  const unavailableCount = Object.values(sources).filter((source) => source.available === false).length;

  const setupItems = [
    {
      title: "Master data upload",
      description: "No master-upload or import-history endpoint exists in the current frontend API.",
      status: "unavailable",
    },
    {
      title: "At least one active programme is available",
      description: courses ? `${activeCourses} of ${courses.length} programmes are active.` : "Programme data could not be loaded.",
      status: courses ? (activeCourses > 0 ? "complete" : "pending") : "unavailable",
      href: "/courses",
    },
    {
      title: "Course coordinators assigned",
      description: courses && coordinators ? `${coursesWithoutCoordinator} active programmes currently have no coordinator.` : "Coordinator coverage could not be checked.",
      status: courses && coordinators ? (activeCourses > 0 && coursesWithoutCoordinator === 0 ? "complete" : "pending") : "unavailable",
      href: "/admin/faculty",
    },
    {
      title: "Subjects and experts configured",
      description: subjects && experts ? `${subjectsWithoutExpert} subjects currently have no subject expert.` : "Subject-expert coverage could not be checked.",
      status: subjects && experts ? (subjects.length > 0 && subjectsWithoutExpert === 0 ? "complete" : "pending") : "unavailable",
      href: "/admin/faculty",
    },
    {
      title: "At least one active student and faculty account exists",
      description: students && faculty
        ? `${activeStudents} active student ${activeStudents === 1 ? "account" : "accounts"} and ${activeFaculty} active faculty ${activeFaculty === 1 ? "account" : "accounts"}.`
        : "Account activation could not be checked.",
      status: students && faculty ? (activeStudents > 0 && activeFaculty > 0 ? "complete" : "pending") : "unavailable",
      href: "/admin/students",
    },
    {
      title: "Configuration readiness audit",
      description: "No consolidated configuration-readiness endpoint exists in the current system.",
      status: "unavailable",
    },
  ];

  if (!user) {
    return (
      <>
        <Head>
          <title>Administrator Overview | SYS</title>
          <meta name="description" content="SYS administrator operations and readiness dashboard." />
        </Head>
        <main className={styles.authorizationGate}>
          {pageError ? (
            <div role="alert">
              <XCircleIcon aria-hidden="true" />
              <h1>Administrator workspace unavailable</h1>
              <p>{pageError}</p>
              <Link href="/login">Return to login</Link>
            </div>
          ) : (
            <div role="status" aria-live="polite">
              <span aria-hidden="true" />
              <h1>Verifying administrator access</h1>
              <p>SYS is confirming your account before opening the workspace.</p>
            </div>
          )}
        </main>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>Administrator Overview | SYS</title>
        <meta name="description" content="SYS administrator operations and readiness dashboard." />
      </Head>
      <AdminShell user={user} notificationFailures={failedNotifications || 0}>
        <div className={styles.dashboardContent}>
          <section className={styles.pageHeading}>
            <div>
              <p className={styles.eyebrow}>Administrator workspace</p>
              <h1>Overview</h1>
              <p>Monitor verified academic setup, account readiness and operational attention across SYS.</p>
            </div>
            <button type="button" onClick={() => setReloadKey((key) => key + 1)} disabled={loading}>
              <ArrowPathIcon aria-hidden="true" /> {loading ? "Refreshing…" : "Refresh data"}
            </button>
          </section>

          {pageError && (
            <section className={styles.pageError} role="alert">
              <XCircleIcon aria-hidden="true" />
              <div><strong>Dashboard unavailable</strong><p>{pageError}</p></div>
            </section>
          )}

          {loading && !pageError && (
            <section className={styles.loadingPanel} role="status" aria-live="polite">
              <span aria-hidden="true" /> Loading verified administrator data…
            </section>
          )}

          {!loading && !pageError && (
            <>
              {unavailableCount > 0 && (
                <section className={styles.partialBanner} role="status">
                  <InformationCircleIcon aria-hidden="true" />
                  <p><strong>Partial live data.</strong> {unavailableCount} administrator data {unavailableCount === 1 ? "source is" : "sources are"} unavailable. Affected cards are labelled rather than estimated.</p>
                </section>
              )}

              <section className={styles.metricsGrid} aria-label="Current account and programme totals">
                <MetricCard icon={UsersIcon} label="Active students" value={activeStudents} note={`${students?.length || 0} total student ${students?.length === 1 ? "account" : "accounts"}`} available={students !== null} />
                <MetricCard icon={UserGroupIcon} label="Active faculty" value={activeFaculty} note={`${faculty?.length || 0} total faculty ${faculty?.length === 1 ? "account" : "accounts"}`} available={faculty !== null} />
                <MetricCard icon={AcademicCapIcon} label="Active programmes" value={activeCourses} note={`${courses?.length || 0} programmes configured`} available={courses !== null} />
                <MetricCard icon={BookOpenIcon} label="Configured subjects" value={subjects?.length} note="Across available programmes" available={subjects !== null} />
              </section>

              <section className={styles.sectionBlock} aria-labelledby="attention-title">
                <div className={styles.sectionHeading}>
                  <div><p className={styles.eyebrow}>Operational review</p><h2 id="attention-title">Needs attention</h2></div>
                  <span>Derived from current SYS records</span>
                </div>
                <div className={styles.attentionGrid}>
                  <AttentionCard title="Programmes without coordinators" count={coursesWithoutCoordinator} available={Boolean(courses && coordinators)} description="Active programmes need a course coordinator assignment." href="/admin/faculty" action="Review responsibilities" />
                  <AttentionCard title="Subjects without experts" count={subjectsWithoutExpert} available={Boolean(subjects && experts)} description="Configured subjects need an assigned subject expert." href="/admin/faculty" action="Assign subject experts" />
                  <AttentionCard title="Incomplete account records" count={students && faculty ? incompleteStudents + incompleteFaculty : null} available={Boolean(students && faculty)} description="Active accounts are missing a required institutional identifier or profile field." href="/admin/students" action="Review accounts" />
                  <AttentionCard title="Notification failures in latest results" count={failedNotifications} available={notifications !== null} description={failedNotifications === 0 ? "No failures found in the latest notification results." : "The latest notification results include a failure status or reason."} href="/admin/notifications" action="Open notifications" />
                </div>
              </section>

              <div className={styles.dashboardColumns}>
                <section className={styles.sectionCard} aria-labelledby="setup-title">
                  <div className={styles.cardHeading}>
                    <span className={styles.headingIcon}><ClipboardDocumentCheckIcon aria-hidden="true" /></span>
                    <div><h2 id="setup-title">Institution setup checklist</h2><p>Live checks where supporting APIs exist.</p></div>
                  </div>
                  <div className={styles.checklist}>
                    {setupItems.map((item) => (
                      <div className={styles.checklistRow} key={item.title}>
                        <div><strong>{item.title}</strong><p>{item.description}</p>{item.href && <Link href={item.href}>Open setup <ChevronRightIcon aria-hidden="true" /></Link>}</div>
                        <StatusPill status={item.status} />
                      </div>
                    ))}
                  </div>
                </section>

                <aside className={styles.quickPanel} aria-labelledby="quick-title">
                  <div className={styles.cardHeading}>
                    <span className={styles.headingIcon}><WrenchScrewdriverIcon aria-hidden="true" /></span>
                    <div><h2 id="quick-title">Quick actions</h2><p>Verified administrative routes.</p></div>
                  </div>
                  <div className={styles.quickLinks}>
                    <Link href="/admin/students/new"><UsersIcon aria-hidden="true" /><span><strong>Add a student</strong><small>Create an institutional account</small></span><ChevronRightIcon aria-hidden="true" /></Link>
                    <Link href="/admin/faculty/new"><UserGroupIcon aria-hidden="true" /><span><strong>Add faculty</strong><small>Create a faculty account</small></span><ChevronRightIcon aria-hidden="true" /></Link>
                    <Link href="/courses/new"><AcademicCapIcon aria-hidden="true" /><span><strong>Create a programme</strong><small>Define programme metadata</small></span><ChevronRightIcon aria-hidden="true" /></Link>
                    <Link href="/admin/faculty"><ShieldCheckIcon aria-hidden="true" /><span><strong>Assign responsibilities</strong><small>Coordinators and subject experts</small></span><ChevronRightIcon aria-hidden="true" /></Link>
                  </div>
                </aside>
              </div>

              <section className={styles.sectionBlock} aria-labelledby="governance-title">
                <div className={styles.sectionHeading}>
                  <div><p className={styles.eyebrow}>Academic governance</p><h2 id="governance-title">Course responsibility model</h2></div>
                </div>
                <div className={styles.governanceGrid}>
                  <article><span>01</span><h3>Administrator</h3><p>Owns programme metadata, scope, faculty assignment and activation.</p></article>
                  <article><span>02</span><h3>Course coordinator</h3><p>Supervises detailed programme structure and academic delivery.</p></article>
                  <article><span>03</span><h3>Subject expert</h3><p>Owns content for assigned subjects, units and topics.</p></article>
                </div>
                <div className={styles.governanceNotes}>
                  <p><CheckCircleIcon aria-hidden="true" /> English Communication is separately enrolable through its own programme configuration.</p>
                  <p><CheckCircleIcon aria-hidden="true" /> Motivation and student support remain cross-cutting services rather than programme ownership.</p>
                  <p><InformationCircleIcon aria-hidden="true" /> Administrative overrides require an auditable record; no audit-log endpoint is currently available.</p>
                </div>
              </section>

              <section className={styles.auditGrid}>
                <details className={styles.detailsCard}>
                  <summary><span><ShieldCheckIcon aria-hidden="true" /> System and configuration readiness</span><ChevronRightIcon aria-hidden="true" /></summary>
                  <div>
                    <p>SYS can currently verify account activation, programme activation, coordinator coverage and subject-expert coverage from live APIs.</p>
                    <p className={styles.unavailableNote}><InformationCircleIcon aria-hidden="true" /> A consolidated readiness score is not shown because no readiness-audit endpoint exists.</p>
                  </div>
                </details>
                <details className={styles.detailsCard}>
                  <summary><span><CloudArrowUpIcon aria-hidden="true" /> Imports and validation</span><ChevronRightIcon aria-hidden="true" /></summary>
                  <div>
                    <p>No master-upload, import history, duplicate-record report or failed-row endpoint is available in the current frontend API.</p>
                    <p className={styles.unavailableNote}><InformationCircleIcon aria-hidden="true" /> Import counts and validation rows are intentionally unavailable.</p>
                  </div>
                </details>
                <details className={styles.detailsCard}>
                  <summary><span><BellAlertIcon aria-hidden="true" /> Recent administrative activity</span><ChevronRightIcon aria-hidden="true" /></summary>
                  <div>
                    <p>No audit-log or recent-activity endpoint is available. SYS does not invent administrative events.</p>
                    <p className={styles.unavailableNote}><InformationCircleIcon aria-hidden="true" /> Activity will appear here when a verified audit source is connected.</p>
                  </div>
                </details>
              </section>
            </>
          )}
        </div>
      </AdminShell>
    </>
  );
}

AdminDashboardPage.getLayout = (page) => page;
