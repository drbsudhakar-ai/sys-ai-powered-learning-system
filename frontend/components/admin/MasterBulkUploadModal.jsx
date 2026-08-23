import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  DocumentCheckIcon,
  InformationCircleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import * as XLSX from "xlsx";
import { adminBulkUploadFaculty, adminBulkUploadStudents, getApiErrorMessage } from "../../src/api";
import BulkUploadSummary from "./BulkUploadSummary";
import styles from "./MasterBulkUploadModal.module.css";

const COMMON_COLUMNS = [
  ["name", "Full name"],
  ["email", "Email address"],
  ["mobile_number", "Mobile number"],
  ["college", "College"],
  ["department", "Department"],
];

const CONFIG = {
  student: {
    label: "Student",
    plural: "students",
    identifier: "roll_number",
    template: "/templates/student_upload_template.csv",
    submit: adminBulkUploadStudents,
    columns: [
      ["roll_number", "Roll number"], ...COMMON_COLUMNS,
      ["academic_program", "Academic programme"], ["admission_year", "Admission year"],
      ["present_year", "Present year"], ["academic_status", "Academic status"],
    ],
  },
  faculty: {
    label: "Faculty",
    plural: "faculty members",
    identifier: "employee_code",
    template: "/templates/faculty_upload_template.csv",
    submit: adminBulkUploadFaculty,
    columns: [
      ["employee_code", "Employee code"], ...COMMON_COLUMNS,
      ["designation", "Designation"], ["employment_status", "Employment status"],
    ],
  },
};

function cleanValue(value) {
  return value === undefined || value === null ? "" : String(value).trim();
}

function validateRows(parsed, config) {
  const valid = [];
  const invalid = [];
  const identifiers = new Set();
  const emails = new Set();
  const mobiles = new Set();

  parsed.forEach((source, index) => {
    const row = Object.fromEntries(config.columns.map(([key]) => [key, cleanValue(source[key])]));
    const missing = config.columns.filter(([key]) => !row[key]).map(([, label]) => label);
    const identifier = row[config.identifier].toUpperCase();
    const email = row.email.toLowerCase();
    const mobile = row.mobile_number.replace(/[\s().-]/g, "");
    let reason = "";

    if (missing.length) reason = `Missing ${missing.join(", ")}`;
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) reason = "Enter a valid email address";
    else if (!/^(?:\+91|91)?[6-9]\d{9}$/.test(mobile) && !/^\+[1-9]\d{7,14}$/.test(mobile)) reason = "Enter a valid mobile number";
    else if (identifiers.has(identifier)) reason = `${config.label} identifier appears more than once`;
    else if (emails.has(email)) reason = "Email address appears more than once";
    else if (mobiles.has(mobile)) reason = "Mobile number appears more than once";
    else if (config.identifier === "employee_code" && !["ACTIVE", "INACTIVE"].includes(row.employment_status.toUpperCase())) reason = "Employment status must be ACTIVE or INACTIVE";
    else if (config.identifier === "roll_number" && !["ACTIVE", "INACTIVE"].includes(row.academic_status.toUpperCase())) reason = "Academic status must be ACTIVE or INACTIVE";

    if (reason) {
      invalid.push({ row: index + 2, reason });
      return;
    }
    identifiers.add(identifier);
    emails.add(email);
    mobiles.add(mobile);
    valid.push({ ...row, [config.identifier]: identifier, email, role: config.identifier === "roll_number" ? "student" : "faculty" });
  });

  return { valid, invalid };
}

export default function MasterBulkUploadModal({ kind, onClose, onUploaded }) {
  const config = CONFIG[kind];
  const closeRef = useRef(null);
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [rows, setRows] = useState([]);
  const [errors, setErrors] = useState([]);
  const [failure, setFailure] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    function handleKeyDown(event) {
      if (event.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [busy, onClose]);

  async function readFile(selected) {
    if (!selected) return;
    setFailure("");
    setResult(null);
    setFile(selected);
    try {
      const data = await selected.arrayBuffer();
      const workbook = XLSX.read(data, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const parsed = XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
      if (!parsed.length) throw new Error("The selected spreadsheet does not contain any data rows.");
      if (parsed.length > 500) throw new Error("Upload a maximum of 500 records at a time.");
      const headers = Object.keys(parsed[0]);
      const missingHeaders = config.columns.filter(([key]) => !headers.includes(key)).map(([, label]) => label);
      if (missingHeaders.length) throw new Error(`Missing template columns: ${missingHeaders.join(", ")}. Download the latest template and try again.`);
      const validated = validateRows(parsed, config);
      setRows(validated.valid);
      setErrors(validated.invalid);
    } catch (error) {
      setRows([]);
      setErrors([]);
      setFailure(error.message || "The spreadsheet could not be read.");
    }
  }

  function removeFile() {
    setFile(null);
    setRows([]);
    setErrors([]);
    setFailure("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function confirmUpload() {
    if (!rows.length || busy) return;
    setBusy(true);
    setFailure("");
    try {
      const response = await config.submit(rows);
      const outcome = response.data;
      setResult(outcome);
      if (Number(outcome?.inserted || 0) > 0) onUploaded?.(outcome);
    } catch (error) {
      setFailure(getApiErrorMessage(error, `${config.label} upload failed. Please try again.`));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.backdrop} onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby={`${kind}-upload-title`}>
        <header className={styles.header}>
          <div className={styles.brand}>
            <span className={styles.brandMark}><Image src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png" alt="" width={52} height={50} /></span>
            <div><span className={styles.eyebrow}>SYS · People & Access</span><h2 id={`${kind}-upload-title`}>Upload {config.label} Master Data</h2><p>Import verified institutional records for secure first-time registration.</p></div>
          </div>
          <button ref={closeRef} type="button" className={styles.iconButton} aria-label="Close upload dialog" onClick={onClose} disabled={busy}><XMarkIcon aria-hidden="true" /></button>
        </header>

        {result ? <BulkUploadSummary result={result} kind={kind} onClose={onClose} /> : (
          <>
            <div className={styles.body}>
              <div className={styles.instructions}><InformationCircleIcon aria-hidden="true" /><span>Use the SYS template, provide every required column, and upload up to 500 {config.plural} in one batch.</span><a href={config.template} download><ArrowDownTrayIcon aria-hidden="true" /> Download template</a></div>
              <div className={`${styles.dropzone} ${dragging ? styles.dropzoneActive : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); readFile(event.dataTransfer.files?.[0]); }}>
                <input ref={inputRef} id={`${kind}-master-upload-file`} className={styles.hiddenInput} type="file" accept=".csv,.xlsx,.xls" onChange={(event) => readFile(event.target.files?.[0])} />
                <ArrowUpTrayIcon className={styles.uploadIcon} aria-hidden="true" />
                <strong>Drag and drop your spreadsheet here</strong>
                <span>CSV, XLSX, or XLS · Maximum 500 records</span>
                <label htmlFor={`${kind}-master-upload-file`} className={styles.secondaryButton}>Choose file</label>
              </div>
              {file && <div className={styles.selectedFile}><DocumentCheckIcon aria-hidden="true" /><div><strong>{file.name}</strong><span>{rows.length} valid record{rows.length === 1 ? "" : "s"}{errors.length ? ` · ${errors.length} requiring attention` : ""}</span></div><button type="button" aria-label="Remove selected file" onClick={removeFile}><XMarkIcon aria-hidden="true" /></button></div>}
              {failure && <div className={styles.errorBanner} role="alert">{failure}</div>}
              {errors.length > 0 && <div className={styles.validationPanel} role="status"><strong>{errors.length} record{errors.length === 1 ? "" : "s"} excluded from upload</strong><ul>{errors.map((error) => <li key={`${error.row}-${error.reason}`}>Row {error.row}: {error.reason}</li>)}</ul></div>}
              {rows.length > 0 && <section className={styles.preview}><div className={styles.previewHeading}><h3>Preview valid records</h3><span>{rows.length} ready to import</span></div><div className={styles.tableWrap}><table><thead><tr>{config.columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{rows.slice(0, 25).map((row) => <tr key={row[config.identifier]}>{config.columns.map(([key]) => <td key={key}>{row[key]}</td>)}</tr>)}</tbody></table></div>{rows.length > 25 && <p className={styles.previewNote}>Showing the first 25 of {rows.length} valid records.</p>}</section>}
            </div>
            <footer className={styles.footer}><span>{rows.length ? `${rows.length} ${config.plural} ready for upload` : "Select a completed SYS template to continue"}</span><div><button type="button" className={styles.secondaryButton} onClick={onClose} disabled={busy}>Cancel</button><button type="button" className={styles.primaryButton} onClick={confirmUpload} disabled={!rows.length || busy}>{busy ? "Uploading…" : `Import ${config.label} Records`}</button></div></footer>
          </>
        )}
      </section>
    </div>
  );
}
