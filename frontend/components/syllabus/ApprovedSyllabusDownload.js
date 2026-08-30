import { useState } from "react";
import { downloadApprovedSyllabus } from "../../src/api";
import { downloadBlob } from "../../src/adminMaster";
import styles from "./SyllabusReview.module.css";
export default function ApprovedSyllabusDownload({ courseId, subjectId, revision, label = "Download syllabus PDF" }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  async function download() {
    setBusy(true); setError("");
    try {
      const response = await downloadApprovedSyllabus(courseId, { subject_id: subjectId, revision });
      downloadBlob(response.data, `SYS_Approved_Syllabus_${courseId}${subjectId ? `_Subject_${subjectId}` : ""}${revision ? `_v${revision}` : ""}.pdf`);
    } catch (err) {
      let message = "Unable to download. Check your access and whether a syllabus version has been approved.";
      try { const body = JSON.parse(await err.response.data.text()); if (typeof body.detail === "string") message = body.detail; } catch {}
      setError(message);
    } finally { setBusy(false); }
  }
  return <div className={styles.download}><button type="button" className={styles.button} onClick={download} disabled={busy}>{busy ? "Preparing PDF…" : label}</button>{error && <p role="alert" className={styles.error}>{error}</p>}</div>;
}
