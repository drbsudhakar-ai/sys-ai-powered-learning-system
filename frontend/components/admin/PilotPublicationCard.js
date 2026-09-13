import { useEffect, useState } from "react";
import { getApiErrorMessage, getPilotPublicationReadiness, publishPilotCourse } from "../../src/api";
import styles from "./CourseMasterWorkspace.module.css";

export default function PilotPublicationCard({ course, onPublished }) {
  const [readiness, setReadiness] = useState(null);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);
  useEffect(() => { if (course?.governance_mode === "PILOT") getPilotPublicationReadiness(course.id)
    .then(({ data }) => setReadiness(data)).catch((requestError) => setError(getApiErrorMessage(requestError, "Unable to load pilot readiness."))); }, [course?.governance_mode, course?.id]);
  if (course?.governance_mode !== "PILOT") return null;
  async function publish() {
    const summary = (readiness?.checks || []).map((item) => `${item.complete ? "✓" : "✗"} ${item.label}`).join("\n");
    if (!window.confirm(`Publish this controlled pilot?\n\n${summary}\n\nIt will not be represented as institutionally approved.`)) return;
    const courseCode = window.prompt(`Enter the exact course code (${course.programme_code}):`); if (courseCode === null) return;
    const reason = window.prompt("Record the controlled pilot publication reason:"); if (reason === null) return;
    setPublishing(true); setError("");
    try { const { data } = await publishPilotCourse(course.id, { course_code: courseCode.trim(), reason: reason.trim(), activate_pending: true, expected_pending_count: readiness.pending_enrollment_count }); setReadiness(data); onPublished?.(); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to publish the controlled pilot.")); }
    finally { setPublishing(false); }
  }
  return <section className={`${styles.detailCard} ${styles.detailCardWide}`}><h2>Controlled pilot publication readiness</h2><p>This separate path never satisfies or replaces institutional publication approval.</p>{error && <div className={styles.error}>{error}</div>}<div className={styles.readiness}>{(readiness?.checks || []).map((item) => <div className={styles.readyItem} key={item.key}><div><strong>{item.label}</strong><small>{item.detail}</small></div><span className={item.complete ? styles.readyYes : styles.readyNo}>{item.complete ? "Complete" : "Needs attention"}</span></div>)}</div><div className={styles.notice}>Controlled Pilot — Not Institutionally Approved</div><div className={styles.actions}><button type="button" className={styles.button} disabled={publishing || !readiness?.ready || course.publication_status === "PILOT_PUBLISHED"} onClick={publish}>{course.publication_status === "PILOT_PUBLISHED" ? "Pilot published" : publishing ? "Publishing…" : "Publish controlled pilot"}</button></div></section>;
}
