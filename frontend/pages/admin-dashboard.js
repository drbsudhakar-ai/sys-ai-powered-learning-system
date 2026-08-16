import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  AcademicCapIcon,
  ArrowPathIcon,
  BellAlertIcon,
  BookOpenIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  ClipboardDocumentCheckIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PresentationChartLineIcon,
  UserGroupIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import AdminShell from "../components/admin/AdminShell";
import BrandedState from "../components/admin/BrandedState";
import useAdminAccess from "../components/admin/useAdminAccess";
import styles from "../components/admin/AdminDashboard.module.css";
import { getAdminOperationsSummary, getApiErrorMessage } from "../src/api";
import { clearSession, roleDisplayLabel } from "../src/auth";
import { isOperationsSummary } from "../src/adminMaster";

const QUICK_ACTIONS = [
  { label: "Add student", detail: "Create an individual student master record", href: "/admin/students/new", icon: UsersIcon },
  { label: "Add faculty", detail: "Create an individual faculty master record", href: "/admin/faculty/new", icon: UserGroupIcon },
  { label: "Create programme", detail: "Open the existing programme creation flow", href: "/courses/new", icon: AcademicCapIcon },
  { label: "Assign responsibility", detail: "Select faculty and assign academic ownership", href: "/admin/faculty", icon: PresentationChartLineIcon },
  { label: "Send notification", detail: "Use the existing notification workspace", href: "/admin/notifications", icon: BellAlertIcon },
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function ReadinessStatus({ status }) {
  const label = status === "complete" ? "Complete" : status === "needs_attention" ? "Needs attention" : "Unavailable";
  const Icon = status === "complete" ? CheckCircleIcon : status === "needs_attention" ? ExclamationTriangleIcon : InformationCircleIcon;
  return <span className={`${styles.readinessStatus} ${styles[`readiness_${status}`]}`}><Icon aria-hidden="true" />{label}</span>;
}

function MetricCard({ icon: Icon, title, value, detail, state = "available" }) {
  return (
    <article className={styles.metricCard} aria-busy={state === "loading"}>
      <span className={styles.metricIcon}><Icon aria-hidden="true" /></span>
      <div>
        <p>{title}</p>
        <strong>{state === "loading" ? "…" : state === "available" ? value : "Unavailable"}</strong>
        <span>{state === "available" ? detail : state === "loading" ? "Loading current data" : "The source returned invalid or unavailable data."}</span>
      </div>
    </article>
  );
}

function EmptyOperationalState({ message }) {
  return <div className={styles.emptyOperational}><InformationCircleIcon aria-hidden="true" /><p>{message}</p></div>;
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const access = useAdminAccess();
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    let active = true;
    setStatus("loading");
    setError("");
    getAdminOperationsSummary({ signal: controller.signal })
      .then((response) => {
        if (!active) return;
        if (!isOperationsSummary(response?.data)) {
          setData(null);
          setStatus("unavailable");
          return;
        }
        setData(response.data);
        setStatus("available");
      })
      .catch(async (requestError) => {
        if (!active || requestError?.code === "ERR_CANCELED") return;
        if (requestError?.response?.status === 401) {
          clearSession();
          await router.replace("/login?reason=expired");
          return;
        }
        if (requestError?.response?.status === 403) {
          await router.replace("/login?reason=unauthorized");
          return;
        }
        setError(getApiErrorMessage(requestError, "SYS operations data could not be loaded."));
        setStatus("error");
      });
    return () => { active = false; controller.abort(); };
  }, [access.status, refreshKey, router]);

  if (access.status === "checking") return <BrandedState />;
  if (access.status === "error") return <BrandedState type="error" title="Administrator workspace unavailable" message={access.error} actionHref="/login" actionLabel="Return to login" />;

  const metricState = status === "loading" ? "loading" : data ? "available" : "unavailable";
  const activity = data?.recent_admin_activity;
  const operations = data?.recent_operations;
  const name = typeof access.user?.name === "string" && access.user.name.trim() ? access.user.name.trim() : null;

  return (
    <>
      <Head><title>Operations Overview | SYS</title><meta name="description" content="SYS administrator operations and readiness dashboard." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
      <AdminShell user={access.user} unreadNotifications={data?.unread_notifications || 0} pageTitle="Operations Overview" scopeLabel={data?.scope_label}>
        <div className={styles.dashboardContent}>
          <section className={styles.welcomeHeader}>
            <div>
              <p className={styles.eyebrow}>Administrator workspace</p>
              <h1>{name ? `${greeting()}, ${name}` : "Welcome back"}</h1>
              <p>Review current master-data readiness, academic operations and actionable attention across your authorized scope.</p>
              <div className={styles.scopeBadges}>
                <span>{access.user?.role === "super_admin" ? "Super Admin" : "Institution Admin"}</span>
                {data?.scope_label && <span>{data.scope_label}</span>}
              </div>
            </div>
            <div className={styles.refreshArea}>
              <button type="button" onClick={() => setRefreshKey((value) => value + 1)} disabled={status === "loading"}><ArrowPathIcon aria-hidden="true" />{status === "loading" ? "Refreshing…" : "Refresh data"}</button>
              <span>{data?.generated_at ? `Last updated ${new Date(data.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Not updated yet"}</span>
            </div>
          </section>

          {status === "error" && <div className={styles.pageError} role="alert"><ExclamationTriangleIcon aria-hidden="true" /><div><strong>Operations data unavailable</strong><p>{error}</p></div></div>}
          {status === "unavailable" && <div className={styles.partialBanner} role="status"><InformationCircleIcon aria-hidden="true" /><p>The operations endpoint returned a malformed response. Counts and readiness are shown as unavailable.</p></div>}

          <section className={styles.metricsGrid} aria-label="Operations summary">
            <MetricCard icon={UsersIcon} title="Students" state={metricState} value={data?.students.total} detail={`${data?.students.active} active · ${data?.students.pending_activation} pending activation`} />
            <MetricCard icon={UserGroupIcon} title="Faculty" state={metricState} value={data?.faculty.total} detail={`${data?.faculty.active} active · ${data?.faculty.pending_activation} pending activation`} />
            <MetricCard icon={AcademicCapIcon} title="Programmes" state={metricState} value={data?.programmes.total} detail={`${data?.programmes.active} active · ${data?.programmes.draft} draft`} />
            <MetricCard icon={ExclamationTriangleIcon} title="Attention Required" state={metricState} value={data?.attention_required.total} detail="Validated actionable items across available sources" />
          </section>

          <section className={styles.sectionBlock} aria-labelledby="quick-actions-title">
            <div className={styles.sectionHeading}><div><p>Working routes</p><h2 id="quick-actions-title">Quick actions</h2></div></div>
            <div className={styles.quickActions}>{QUICK_ACTIONS.map(({ label, detail, href, icon: Icon }) => <Link key={href + label} href={href}><Icon aria-hidden="true" /><span><strong>{label}</strong><small>{detail}</small></span><ChevronRightIcon aria-hidden="true" /></Link>)}</div>
          </section>

          <section className={styles.sectionBlock} aria-labelledby="attention-title">
            <div className={styles.sectionHeading}><div><p>Validated API data</p><h2 id="attention-title">Attention required</h2></div></div>
            {data ? (
              <div className={styles.attentionGrid}>{data.attention.map((item) => <article key={item.key}><span className={item.count > 0 ? styles.attentionOpen : styles.attentionClear}>{item.count > 0 ? <ExclamationTriangleIcon aria-hidden="true" /> : <CheckCircleIcon aria-hidden="true" />}</span><strong>{item.count}</strong><h3>{item.label}</h3><Link href={item.href}>Review records <ChevronRightIcon aria-hidden="true" /></Link></article>)}</div>
            ) : <EmptyOperationalState message="Attention checks are unavailable until the operations response is valid." />}
          </section>

          <section className={styles.readinessCard} aria-labelledby="readiness-title">
            <details open>
              <summary><span><CheckCircleIcon aria-hidden="true" /><span><strong id="readiness-title">Setup & Operational Readiness</strong><small>Exact predicates from available platform data</small></span></span><ChevronRightIcon aria-hidden="true" /></summary>
              <div className={styles.readinessList}>
                {data ? data.readiness.map((item) => <div key={item.key}><div><strong>{item.label}</strong><p>{item.detail}</p></div><ReadinessStatus status={item.status} /></div>) : <EmptyOperationalState message="Readiness checks are unavailable." />}
              </div>
            </details>
          </section>

          <section className={styles.operationsGrid} aria-label="Operational panels">
            <article>
              <div className={styles.panelHeading}><span><AcademicCapIcon aria-hidden="true" /></span><div><h2>Academic Operations</h2><p>Current configured academic structures</p></div></div>
              {data ? <dl className={styles.compactStats}><div><dt>Programmes</dt><dd>{data.academic_operations.programmes}</dd></div><div><dt>Subjects</dt><dd>{data.academic_operations.subjects}</dd></div><div><dt>Coordinator assignments</dt><dd>{data.academic_operations.coordinator_assignments}</dd></div><div><dt>Expert assignments</dt><dd>{data.academic_operations.expert_assignments}</dd></div></dl> : <EmptyOperationalState message="Academic operations are unavailable." />}
            </article>

            <article>
              <div className={styles.panelHeading}><span><ClipboardDocumentCheckIcon aria-hidden="true" /></span><div><h2>Recent Assessments & Sessions</h2><p>Latest records from real operation tables</p></div></div>
              {operations && (operations.assessments.length || operations.learning_sessions.length) ? <ul className={styles.operationList}>{operations.assessments.map((item) => <li key={`a-${item.id}`}><Link href={`/assessments/${item.id}`}>{item.title}</Link><span>{item.status} · Assessment</span></li>)}{operations.learning_sessions.map((item) => <li key={`s-${item.id}`}><Link href={`/learning-sessions/${item.id}`}>{item.title}</Link><span>{item.status} · Learning session</span></li>)}</ul> : <EmptyOperationalState message={data ? "No assessments or learning sessions are available yet." : "Recent operations are unavailable."} />}
            </article>

            <article>
              <div className={styles.panelHeading}><span><PresentationChartLineIcon aria-hidden="true" /></span><div><h2>Early Warning Summary</h2><p>Students with high-priority learning gaps</p></div></div>
              {data ? <div className={styles.earlyWarning}><strong>{data.early_warning.students_requiring_attention}</strong><span>students currently require attention</span><Link href="/analytics/admin">Open learning intelligence <ChevronRightIcon aria-hidden="true" /></Link></div> : <EmptyOperationalState message="Early-warning data is unavailable." />}
            </article>

            <article id="system-administration">
              <div className={styles.panelHeading}><span><BookOpenIcon aria-hidden="true" /></span><div><h2>Recent Administrative Activity</h2><p>Security-audited master-data changes</p></div></div>
              {activity?.available ? (activity.items.length ? <ul className={styles.operationList}>{activity.items.map((item) => <li key={item.id}><strong>{item.summary}</strong><span>{new Date(item.created_at).toLocaleString()}</span></li>)}</ul> : <EmptyOperationalState message="No audited administrative changes are available yet." />) : <EmptyOperationalState message={activity?.reason || "Administrative activity is unavailable."} />}
            </article>
          </section>

          <p className={styles.authorityNote}>Signed in as {roleDisplayLabel(access.user?.role)}. Client-side checks supplement, but do not replace, backend authorization.</p>
        </div>
      </AdminShell>
    </>
  );
}

AdminDashboardPage.getLayout = (page) => page;
