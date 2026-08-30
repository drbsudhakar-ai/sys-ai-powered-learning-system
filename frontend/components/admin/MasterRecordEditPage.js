import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import {
  AcademicCapIcon,
  ArrowLeftIcon,
  CameraIcon,
  CheckCircleIcon,
  IdentificationIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  TrashIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import {
  adminGetFaculty,
  adminGetStudent,
  adminRemoveFacultyPhoto,
  adminRemoveStudentPhoto,
  adminUpdateFaculty,
  adminUpdateStudent,
  adminUploadFacultyPhoto,
  adminUploadStudentPhoto,
  getAdminOperationsSummary,
  getApiErrorMessage,
} from "../../src/api";
import { normalizeMasterStatus, validateProfilePhoto } from "../../src/adminMaster";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./MasterRecordEditPage.module.css";

const CONFIG = {
  student: {
    label: "Student",
    listHref: "/admin/students",
    identifier: "roll_number",
    identifierLabel: "Roll number",
    status: "academic_status",
    statusLabel: "Academic status",
    get: adminGetStudent,
    update: adminUpdateStudent,
    uploadPhoto: adminUploadStudentPhoto,
    removePhoto: adminRemoveStudentPhoto,
  },
  faculty: {
    label: "Faculty",
    listHref: "/admin/faculty",
    identifier: "employee_code",
    identifierLabel: "Employee code",
    status: "employment_status",
    statusLabel: "Employment status",
    get: adminGetFaculty,
    update: adminUpdateFaculty,
    uploadPhoto: adminUploadFacultyPhoto,
    removePhoto: adminRemoveFacultyPhoto,
  },
};

const EMPTY = {
  name: "", email: "", mobile_number: "", roll_number: "", employee_code: "",
  college: "", academic_program: "", admission_year: "", present_year: "",
  academic_status: "ACTIVE", department: "", designation: "",
  employment_status: "ACTIVE", password: "", photo_url: "",
};

function normalizeMobile(value) {
  const cleaned = String(value || "").trim().replace(/[\s().-]/g, "");
  if (/^[6-9]\d{9}$/.test(cleaned)) return `+91${cleaned}`;
  if (/^91[6-9]\d{9}$/.test(cleaned)) return `+${cleaned}`;
  return cleaned || null;
}

function initials(name) {
  return String(name || "SYS").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function Field({ id, label, value, onChange, required, hint, children, ...props }) {
  return <label className={styles.field} htmlFor={id}><span>{label}{required ? <i> *</i> : null}</span>{children || <input id={id} name={id} value={value} onChange={onChange} required={required} {...props} />}{hint ? <small>{hint}</small> : null}</label>;
}

export default function MasterRecordEditPage({ kind }) {
  const config = CONFIG[kind];
  const router = useRouter();
  const { id } = router.query;
  const access = useAdminAccess();
  const [form, setForm] = useState(EMPTY);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [summary, setSummary] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const localPreview = useMemo(() => photoFile ? URL.createObjectURL(photoFile) : "", [photoFile]);
  useEffect(() => () => { if (localPreview) URL.revokeObjectURL(localPreview); }, [localPreview]);

  useEffect(() => {
    if (access.status !== "ready" || !router.isReady || !id) return undefined;
    const controller = new AbortController();
    Promise.all([config.get(id), getAdminOperationsSummary({ signal: controller.signal }).catch(() => null)])
      .then(([response, summaryResponse]) => {
        const record = kind === "faculty" ? (response.data.faculty || response.data) : response.data;
        const isRegistered = record.registration_complete === true;
        setRegistrationComplete(isRegistered);
        setSummary(summaryResponse?.data || null);
        setForm({
          ...EMPTY,
          name: record.name || "",
          email: record.institutional_email || record.email || "",
          mobile_number: record.institutional_mobile || record.mobile_number || "",
          [config.identifier]: record[config.identifier] || "",
          college: record.college || "",
          academic_program: record.academic_program || "",
          admission_year: record.admission_year || "",
          present_year: record.present_year || "",
          academic_status: normalizeMasterStatus(record.academic_status),
          department: record.department || "",
          designation: record.designation || "",
          employment_status: normalizeMasterStatus(record.employment_status),
          photo_url: record.photo_url || "",
        });
      })
      .catch((requestError) => setError(getApiErrorMessage(requestError, `Unable to load the ${config.label.toLowerCase()} record.`)))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [access.status, config, id, kind, router.isReady]);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function choosePhoto(event) {
    const file = event.target.files?.[0] || null;
    if (!file) return;
    const validationError = validateProfilePhoto(file);
    if (validationError) {
      setError(validationError);
      event.target.value = "";
      return;
    }
    setError("");
    setPhotoFile(file);
    setRemovePhoto(false);
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    if (!form.name.trim() || !form[config.identifier].trim()) {
      setError(`Full name and ${config.identifierLabel.toLowerCase()} are required.`);
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim() || null,
        mobile_number: normalizeMobile(form.mobile_number),
        [config.identifier]: form[config.identifier].trim().toUpperCase(),
        college: form.college.trim() || null,
        [config.status]: normalizeMasterStatus(form[config.status]),
      };
      if (kind === "student") Object.assign(payload, {
        academic_program: form.academic_program.trim() || null,
        admission_year: form.admission_year ? Number(form.admission_year) : null,
        present_year: form.present_year ? Number(form.present_year) : null,
      });
      else Object.assign(payload, {
        department: form.department.trim() || null,
        designation: form.designation.trim() || null,
      });
      if (form.password) payload.password = form.password;
      await config.update(id, payload);
      if (photoFile) await config.uploadPhoto(id, photoFile);
      else if (removePhoto && form.photo_url) await config.removePhoto(id);
      await router.push(`${config.listHref}/${id}`);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, `Unable to update the ${config.label.toLowerCase()} record.`));
    } finally {
      setSubmitting(false);
    }
  }

  if (access.status === "checking" || loading) return <BrandedState title={`Opening ${config.label.toLowerCase()} editor`} message="Verifying administrator access and loading the master record." />;
  if (access.status === "error") return <BrandedState type="error" title="Administrator access unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  const preview = localPreview || (!removePhoto ? form.photo_url : "");
  return <><Head><title>{`Edit ${config.label} | SYS`}</title><meta name="description" content={`Edit a SYS ${config.label.toLowerCase()} master record.`} /></Head><AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="People & Access" pageTitle={`Edit ${config.label}`} scopeLabel={summary?.scope_label || "Platform-wide"}><main className={styles.workspace}>
    <Link href={`${config.listHref}/${id}`} className={styles.backLink}><ArrowLeftIcon /> Back to {config.label} profile</Link>
    <section className={styles.pageHeading}><div><span>PEOPLE & ACCESS · MASTER RECORDS</span><h1>Edit {config.label} Profile</h1><p>Update institutional identity, contact, academic information, status, and profile photograph.</p></div><span className={styles.accountBadge}>{registrationComplete ? "Registered account" : "Pending registration"}</span></section>
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {error ? <div className={styles.error} role="alert"><InformationCircleIcon />{error}</div> : null}
      <div className={styles.grid}>
        <div className={styles.sections}>
          <section className={styles.card}><header><UserCircleIcon /><div><h2>Identity information</h2><p>Official institutional identity and unique master identifier.</p></div></header><div className={styles.fieldGrid}><Field id="name" label="Full name" value={form.name} onChange={onChange} required /><Field id={config.identifier} label={config.identifierLabel} value={form[config.identifier]} onChange={onChange} required /></div></section>
          <section className={styles.card}><header><ShieldCheckIcon /><div><h2>Institutional contact</h2><p>{registrationComplete ? "Changing a verified login contact requires controlled verification." : "These contact details will be used when the account completes registration."}</p></div></header><div className={styles.fieldGrid}><Field id="email" label="Institutional email" type="email" value={form.email} onChange={onChange} /><Field id="mobile_number" label="Institutional mobile" type="tel" value={form.mobile_number} onChange={onChange} hint="Indian 10-digit numbers are saved with +91." /></div></section>
          <section className={styles.card}><header><AcademicCapIcon /><div><h2>{kind === "student" ? "Academic information" : "Professional information"}</h2><p>Maintain current institutional placement and status.</p></div></header><div className={styles.fieldGrid}><Field id="college" label="College" value={form.college} onChange={onChange} />{kind === "student" ? <><Field id="academic_program" label="Academic programme" value={form.academic_program} onChange={onChange} /><Field id="admission_year" label="Admission year" type="number" min="1900" max="2200" value={form.admission_year} onChange={onChange} /><Field id="present_year" label="Present year" type="number" min="1" max="20" value={form.present_year} onChange={onChange} /></> : <><Field id="department" label="Department" value={form.department} onChange={onChange} /><Field id="designation" label="Designation" value={form.designation} onChange={onChange} /></>}<Field id={config.status} label={config.statusLabel}><select id={config.status} name={config.status} value={form[config.status]} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></Field>{registrationComplete ? <Field id="password" label="New password (optional)" type="password" minLength="8" autoComplete="new-password" value={form.password} onChange={onChange} hint="Leave empty to keep the existing password." /> : null}</div></section>
        </div>
        <aside className={styles.photoCard}><div className={styles.photo}>{preview ? <img src={preview} alt={`${form.name || config.label} profile preview`} /> : <span>{initials(form.name)}</span>}</div><h2>Profile photograph</h2><p>Use a clear institutional portrait. JPEG, PNG or WebP; maximum 5 MB.</p><label className={styles.browse}><CameraIcon /> Browse photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={choosePhoto} /></label>{preview ? <button type="button" className={styles.remove} onClick={() => { setPhotoFile(null); setRemovePhoto(true); }}><TrashIcon /> Remove photo</button> : null}<div className={styles.photoNote}><IdentificationIcon /><span>The uploaded photograph appears in administrator profiles and branded profile documents.</span></div></aside>
      </div>
      <footer><Link href={`${config.listHref}/${id}`} className={styles.cancel}>Cancel</Link><button type="submit" className={styles.save} disabled={submitting}><CheckCircleIcon />{submitting ? "Saving changes…" : "Save profile changes"}</button></footer>
    </form>
  </main></AdminShell></>;
}
