import Head from "next/head";
import Link from "next/link";
import { useState } from "react";
import { enrollInCourse, getApiErrorMessage } from "../../src/api";
import styles from "./StudentCoursesWorkspace.module.css";

const label = (value) => (value || "NOT_STARTED").toLowerCase().replaceAll("_", " ");

export default function StudentCoursesWorkspace({ assignments, catalog, loading, error, onEnrolled }) {
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState("");
  const assigned = new Set(assignments.map((course) => course.id));
  async function enroll(id) {
    setBusy(id); setActionError("");
    try { await enrollInCourse(id); await onEnrolled(); }
    catch (e) { setActionError(getApiErrorMessage(e, "Unable to enroll. Please contact your administrator.")); }
    finally { setBusy(null); }
  }
  return <main className={styles.page}>
    <Head><title>My Courses | SYS</title></Head>
    <header className={styles.hero}><p>SYS · STRENGTHEN YOUR SKILLS</p><h1>My Courses</h1><p>Your learning programmes, progress, and next lesson in one place.</p></header>
    {loading && <p role="status">Loading your courses…</p>}
    {(error || actionError) && <p role="alert" className={styles.error}>{error || actionError}</p>}
    {!loading && !error && <>
      {!assignments.length && <p className={styles.card}>No courses assigned yet. Browse the published catalog below or contact your administrator.</p>}
      <section className={styles.grid} aria-label="My enrolled and assigned courses">
        {assignments.map((course) => <article className={styles.card} key={course.id}>
          <span className={styles.badge}>{label(course.enrollment_status)}</span><h2>{course.title}</h2><p>{course.programme_code}</p>
          {course.can_access ? <>
            <p className={styles.state}>Learning: {label(course.learning?.status)}</p>
            <progress value={course.learning?.completed_topics || 0} max={course.learning?.total_topics || 1} aria-label={`${course.title} completed topics`} />
            <p>{course.learning?.completed_topics || 0} of {course.learning?.total_topics || 0} topics completed</p>
            <div className={styles.actions}><Link href={`/courses/${course.id}/workspace`}>Open syllabus</Link>
              {course.learning?.continue_learning && <Link href={course.learning.continue_learning.classroom_path}>Continue learning</Link>}</div>
          </> : <p className={styles.locked}>Locked · {course.lock_reason}</p>}
        </article>)}
      </section>
      <h2 className={styles.sectionTitle}>Published course catalog</h2><p>Self-enrollment is available only where enabled by your administrator.</p>
      <section className={styles.grid} aria-label="Published course catalog">
        {catalog.map((course) => <article className={styles.card} key={course.id}><h3>{course.title}</h3><p>{course.description || course.target_purpose || "SYS learning programme"}</p>
          {assigned.has(course.id) ? <p>Already listed in My Courses.</p> : course.self_enrollment_enabled ? <button disabled={busy !== null} onClick={() => enroll(course.id)}>{busy === course.id ? "Enrolling…" : "Enroll"}</button> : <p>Administrator enrollment required.</p>}
        </article>)}
        {!catalog.length && <p>No published courses available yet.</p>}
      </section>
    </>}
  </main>;
}
