import Head from "next/head";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AcademicCapIcon, ArrowDownTrayIcon, ArrowPathIcon, EyeIcon, MagnifyingGlassIcon, PencilSquareIcon, PlusIcon } from "@heroicons/react/24/outline";
import { getAdminOperationsSummary, getApiErrorMessage, getCourses } from "../../src/api";
import { COURSE_CATEGORIES, courseCategoryLabel, courseCsv, courseStatusLabel, filterCourses } from "../../src/courseMaster";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./CourseMasterWorkspace.module.css";

function Metric({ label, value, detail }) {
  return <article className={styles.metric}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

export default function CourseMasterWorkspace() {
  const access = useAdminAccess();
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState("name");

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getCourses(undefined, { signal: controller.signal }).then(({ data }) => {
      if (!Array.isArray(data)) throw new Error("SYS returned an invalid course list.");
      setItems(data);
    }).catch((requestError) => {
      if (requestError?.code !== "ERR_CANCELED") setError(getApiErrorMessage(requestError, requestError.message || "Unable to load SYS courses."));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    getAdminOperationsSummary({ signal: controller.signal }).then(({ data }) => setSummary(data || null)).catch(() => {});
    return () => controller.abort();
  }, [access.status, refresh]);

  const filtered = useMemo(() => filterCourses(items, { search, category, status, sort }), [items, search, category, status, sort]);
  const activeCount = items.filter((course) => course.is_active).length;
  const enrolledCount = items.reduce((total, course) => total + Number(course.student_count || 0), 0);

  function exportCurrentView() {
    const url = URL.createObjectURL(new Blob([courseCsv(filtered)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `SYS_Course_Master_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the SYS Course Master workspace." />;
  if (access.status === "error") return <BrandedState type="error" title="Course Master unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  return <>
    <Head><title>Course Master | SYS</title><meta name="description" content="Manage SYS courses, academic readiness, and course enrollment." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
    <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="Academic Management" pageTitle="Course Master" scopeLabel={summary?.scope_label || "Platform-wide"}>
      <main className={styles.workspace}>
        <header className={styles.heading}><div><span className={styles.eyebrow}>Academic management</span><h1>Course Master</h1><p>Manage SYS courses, examination preparation, academic ownership, and course readiness.</p></div><div className={styles.actions}><button type="button" className={styles.button} onClick={() => setRefresh((value) => value + 1)} disabled={loading}><ArrowPathIcon />Refresh</button><button type="button" className={styles.button} onClick={exportCurrentView} disabled={loading || filtered.length === 0}><ArrowDownTrayIcon />Export current view</button><Link href="/admin/academic-responsibilities" className={styles.button}><AcademicCapIcon />Academic ownership</Link><Link href="/admin/courses/new" className={styles.buttonPrimary}><PlusIcon />Create course</Link></div></header>

        <section className={styles.metrics} aria-label="Course summary"><Metric label="Total courses" value={items.length} detail="All SYS academic courses" /><Metric label="Active courses" value={activeCount} detail="Available in the course catalogue" /><Metric label="Draft courses" value={items.length - activeCount} detail="Not yet available to students" /><Metric label="Student enrollments" value={enrolledCount} detail="Recorded across all courses" /></section>

        <section className={styles.panel} aria-label="Course search and filters"><div className={styles.toolbar}><label className={styles.search}><MagnifyingGlassIcon /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by course title, course code, examination, or coordinator" aria-label="Search courses" /></label><select className={styles.select} value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Course category"><option value="all">All categories</option>{COURSE_CATEGORIES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><select className={styles.select} value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Sort courses"><option value="name">Course name</option><option value="recent">Recently created</option><option value="students">Most enrolled</option></select></div><div className={styles.tabs}>{[["all", "All courses"], ["active", "Active"], ["draft", "Draft"], ["needs_attention", "Needs attention"]].map(([value, label]) => <button key={value} type="button" className={`${styles.tab} ${status === value ? styles.tabActive : ""}`} onClick={() => setStatus(value)}>{label}</button>)}</div></section>

        <section className={styles.panel}><div className={styles.tableHeading}><h2>SYS courses</h2><span>{filtered.length} matching {filtered.length === 1 ? "course" : "courses"}</span></div>{error ? <div className={styles.empty}><h3>Course data could not be loaded</h3><p>{error}</p><button type="button" className={styles.buttonPrimary} onClick={() => setRefresh((value) => value + 1)}>Try again</button></div> : loading ? <div className={styles.loading}>Loading current course records…</div> : filtered.length === 0 ? <div className={styles.empty}><AcademicCapIcon /><h3>{items.length ? "No courses match your filters" : "No SYS courses created yet"}</h3><p>{items.length ? "Change the search or filters to find an existing course." : "Create the first course to prepare academic subjects, assign faculty, enroll students, and start learning activities."}</p>{!items.length && <Link className={styles.buttonPrimary} href="/admin/courses/new"><PlusIcon />Create first course</Link>}</div> : <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Course</th><th>Category and exam</th><th>Syllabus</th><th>Faculty</th><th>Students</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map((course) => <tr key={course.id}><td><strong>{course.title}</strong><small>{course.programme_code || "Code unavailable"}</small></td><td><strong>{courseCategoryLabel(course.programme_category)}</strong><small>{course.examination_name || "No examination configured"}</small></td><td><strong>{course.subject_count || 0} subjects · {course.unit_count || 0} units</strong><small>{course.topic_count || 0} topics · {course.subtopic_count || 0} subtopics</small>{course.syllabus_configuration && <small>{course.syllabus_configuration.status === 'WORKING_DRAFT' ? 'Saved working syllabus' : 'Configured syllabus'} · {course.syllabus_configuration.approved_subject_count} approved</small>}</td><td><strong>{course.course_coordinators?.length || 0} coordinators</strong><small>{course.subject_expert_count || 0} subject experts</small></td><td>{course.student_count || 0}</td><td><span className={course.is_active ? styles.statusActive : styles.statusDraft}>{courseStatusLabel(course)}</span></td><td><div className={styles.actions}><Link href={`/admin/courses/${course.id}`} className={styles.button}><EyeIcon />View</Link><Link href={`/admin/courses/${course.id}/syllabus`} className={styles.button}><AcademicCapIcon />Syllabus</Link><Link href={`/admin/courses/${course.id}/edit`} className={styles.button}><PencilSquareIcon />Edit</Link></div></td></tr>)}</tbody></table></div>}</section>
      </main>
    </AdminShell>
  </>;
}
