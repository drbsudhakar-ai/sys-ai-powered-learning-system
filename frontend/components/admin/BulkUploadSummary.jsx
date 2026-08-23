import { CheckCircleIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import styles from "./MasterBulkUploadModal.module.css";

export default function BulkUploadSummary({ result, kind, onClose }) {
  const inserted = Number(result?.inserted || 0);
  const skipped = Number(result?.skipped || 0);
  const invalid = Number(result?.invalid || 0);
  const total = Number(result?.log_entry?.total_uploaded || inserted + skipped + invalid);
  const complete = inserted > 0;
  const Icon = complete ? CheckCircleIcon : ExclamationTriangleIcon;

  return (
    <section className={styles.summary} aria-live="polite">
      <div className={`${styles.summaryIcon} ${complete ? styles.summarySuccess : styles.summaryWarning}`}>
        <Icon aria-hidden="true" />
      </div>
      <h3>{complete ? `${kind === "faculty" ? "Faculty" : "Student"} master updated` : "No new records imported"}</h3>
      <p>
        {complete
          ? "Imported master records are ready for secure first-time registration."
          : "Review the skipped or invalid records before trying another upload."}
      </p>
      <div className={styles.summaryMetrics}>
        {[ ["Processed", total], ["Imported", inserted], ["Skipped", skipped], ["Invalid", invalid] ].map(([label, value]) => (
          <div key={label}><strong>{value}</strong><span>{label}</span></div>
        ))}
      </div>
      {result?.invalid_records?.length > 0 && (
        <div className={styles.validationPanel} role="status">
          <strong>Records requiring attention</strong>
          <ul>{result.invalid_records.map((entry, index) => (
            <li key={`${entry.row || index}-${entry.reason}`}>Row {entry.row || index + 2}: {entry.reason}</li>
          ))}</ul>
        </div>
      )}
      <button type="button" className={styles.primaryButton} onClick={onClose}>Return to master data</button>
    </section>
  );
}
