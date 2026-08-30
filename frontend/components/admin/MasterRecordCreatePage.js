import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  AcademicCapIcon,
  ArrowLeftIcon,
  BuildingLibraryIcon,
  CheckCircleIcon,
  IdentificationIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import {
  adminCreateFaculty,
  adminCreateStudent,
  getAdminOperationsSummary,
  getApiErrorMessage,
} from "../../src/api";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./MasterRecordCreatePage.module.css";

const CONFIG = {
  student: {
    label: "Student",
    listLabel: "Student Master",
    listHref: "/admin/students",
    identifier: "roll_number",
    identifierLabel: "Roll number",
    identifierPlaceholder: "For example, 240334524681001",
    create: adminCreateStudent,
    initial: {
      name: "", email: "", mobile_number: "", roll_number: "", college: "", photo_url: "",
      academic_program: "", admission_year: "", present_year: "", academic_status: "ACTIVE",
    },
  },
  faculty: {
    label: "Faculty",
    listLabel: "Faculty Master",
    listHref: "/admin/faculty",
    identifier: "employee_code",
    identifierLabel: "Employee code",
    identifierPlaceholder: "For example, 602867",
    create: adminCreateFaculty,
    initial: {
      name: "", email: "", mobile_number: "", employee_code: "", college: "", photo_url: "",
      department: "", designation: "", employment_status: "ACTIVE",
    },
  },
};

function normalizeMobile(value) {
  const cleaned = String(value || "").trim().replace(/[\s().-]/g, "");
  if (/^[6-9]\d{9}$/.test(cleaned)) return `+91${cleaned}`;
  if (/^91[6-9]\d{9}$/.test(cleaned)) return `+${cleaned}`;
  return cleaned || null;
}

function Field({ id, label, value, onChange, required = false, hint, children, ...props }) {
  return (
    <label className={styles.field} htmlFor={id}>
      <span>{label}{required && <i aria-hidden="true"> *</i>}</span>
      {children || <input id={id} name={id} value={value} onChange={onChange} required={required} {...props} />}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export default function MasterRecordCreatePage({ kind }) {
  const config = CONFIG[kind];
  const router = useRouter();
  const access = useAdminAccess();
  const [form, setForm] = useState(config.initial);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    getAdminOperationsSummary({ signal: controller.signal })
      .then((response) => setSummary(response?.data || null))
      .catch((requestError) => {
        if (requestError?.code !== "ERR_CANCELED") setSummary(null);
      });
    return () => controller.abort();
  }, [access.status]);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");

    if (!form.name.trim() || !form[config.identifier].trim()) {
      setError(`Full name and ${config.identifierLabel.toLowerCase()} are required.`);
      return;
    }
    if (!form.email.trim() && !form.mobile_number.trim()) {
      setError("Provide at least one institutional contact: email address or mobile number.");
      return;
    }
    if (kind === "student" && !form.academic_program.trim()) {
      setError("Academic programme is required for the student master record.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      email: form.email.trim() || null,
      mobile_number: normalizeMobile(form.mobile_number),
      [config.identifier]: form[config.identifier].trim().toUpperCase(),
      college: form.college.trim() || null,
      photo_url: form.photo_url.trim() || null,
    };

    if (kind === "student") {
      Object.assign(payload, {
        academic_program: form.academic_program.trim(),
        admission_year: form.admission_year ? Number(form.admission_year) : null,
        present_year: form.present_year ? Number(form.present_year) : null,
        academic_status: form.academic_status,
      });
    } else {
      Object.assign(payload, {
        department: form.department.trim() || null,
        designation: form.designation.trim() || null,
        employment_status: form.employment_status,
      });
    }

    setSubmitting(true);
    try {
      await config.create(payload);
      await router.push(config.listHref);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, `Unable to create the ${config.label.toLowerCase()} record.`));
    } finally {
      setSubmitting(false);
    }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing your secure SYS master-data workspace." />;
  if (access.status === "error") return <BrandedState type="error" title="Administrator access unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  return (
    <>
      <Head>
        <title>{`Add ${config.label} | SYS`}</title>
        <meta name="description" content={`Create a secure SYS ${config.label.toLowerCase()} master record.`} />
        <link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" />
      </Head>
      <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="People & Access" pageTitle={`Add ${config.label}`} scopeLabel={summary?.scope_label || "Platform-wide"}>
        <main className={styles.workspace}>
          <Link href={config.listHref} className={styles.backLink}><ArrowLeftIcon aria-hidden="true" /> Back to {config.listLabel}</Link>

          <section className={styles.pageHeading}>
            <div>
              <span className={styles.eyebrow}>People & Access · Master Records</span>
              <h1>Add Individual {config.label}</h1>
              <p>{kind === "student" ? "Create a student master record with its academic programme and secure registration details." : "Add a faculty member with institutional contact information and academic responsibility details."}</p>
            </div>
            <div className={styles.identityBadge}><Image src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png" alt="" width={52} height={50} /><span>Strengthen Your Skills<small>Shape Your Successful Future.</small></span></div>
          </section>

          <div className={styles.contentGrid}>
            <form className={styles.formCard} onSubmit={onSubmit} noValidate>
              <div className={styles.formHeading}><div><span className={styles.sectionIcon}><IdentificationIcon aria-hidden="true" /></span><div><h2>{config.label} master details</h2><p>Fields marked with an asterisk are required.</p></div></div><span className={styles.pendingBadge}>Pending registration</span></div>

              {error && <div className={styles.errorBanner} role="alert"><InformationCircleIcon aria-hidden="true" />{error}</div>}

              <section className={styles.section} aria-labelledby={`${kind}-identity-title`}>
                <div className={styles.sectionHeading}><UserCircleIcon aria-hidden="true" /><div><h3 id={`${kind}-identity-title`}>Identity information</h3><p>Use the official institutional name and unique identifier.</p></div></div>
                <div className={styles.fieldGrid}>
                  <Field id="name" label="Full name" value={form.name} onChange={onChange} placeholder={kind === "student" ? "Enter student's full name" : "Enter faculty member's full name"} autoComplete="name" required />
                  <Field id={config.identifier} label={config.identifierLabel} value={form[config.identifier]} onChange={onChange} placeholder={config.identifierPlaceholder} required />
                  <Field id="photo_url" label="Profile photo URL" value={form.photo_url} onChange={onChange} placeholder="https://example.com/photo.jpg or /photos/photo.jpg" hint="Optional. Use an approved institutional photo URL or public file path." />
                </div>
              </section>

              <section className={styles.section} aria-labelledby={`${kind}-contact-title`}>
                <div className={styles.sectionHeading}><ShieldCheckIcon aria-hidden="true" /><div><h3 id={`${kind}-contact-title`}>Institutional contact</h3><p>Provide at least one verified institutional contact for first-time registration.</p></div></div>
                <div className={styles.fieldGrid}>
                  <Field id="email" label="Institutional email" type="email" value={form.email} onChange={onChange} placeholder="name@example.com" autoComplete="email" />
                  <Field id="mobile_number" label="Institutional mobile" type="tel" value={form.mobile_number} onChange={onChange} placeholder="9876543210 or +919876543210" autoComplete="tel" hint="Indian 10-digit numbers are automatically saved with +91." />
                </div>
              </section>

              <section className={styles.section} aria-labelledby={`${kind}-academic-title`}>
                <div className={styles.sectionHeading}><AcademicCapIcon aria-hidden="true" /><div><h3 id={`${kind}-academic-title`}>{kind === "student" ? "Academic information" : "Professional information"}</h3><p>{kind === "student" ? "Record the college, degree programme, and current academic progress." : "Record the college, department, designation, and employment status."}</p></div></div>
                <div className={styles.fieldGrid}>
                  <Field id="college" label="College" value={form.college} onChange={onChange} placeholder="For example, MJPTBCWRDC-Narayanpet" />
                  {kind === "student" ? (
                    <>
                      <Field id="academic_program" label="Academic programme" value={form.academic_program} onChange={onChange} placeholder="For example, B.Sc.(MPCS)" required />
                      <Field id="admission_year" label="Admission year" type="number" min="1900" max="2200" value={form.admission_year} onChange={onChange} placeholder="2024" />
                      <Field id="present_year" label="Present year" type="number" min="1" max="20" value={form.present_year} onChange={onChange} placeholder="3" />
                      <Field id="academic_status" label="Academic status"><select id="academic_status" name="academic_status" value={form.academic_status} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></Field>
                    </>
                  ) : (
                    <>
                      <Field id="department" label="Department" value={form.department} onChange={onChange} placeholder="For example, Computer Science" />
                      <Field id="designation" label="Designation" value={form.designation} onChange={onChange} placeholder="For example, Degree Lecturer" />
                      <Field id="employment_status" label="Employment status"><select id="employment_status" name="employment_status" value={form.employment_status} onChange={onChange}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></Field>
                    </>
                  )}
                </div>
              </section>

              <footer className={styles.formFooter}><Link href={config.listHref} className={styles.secondaryButton}>Cancel</Link><button type="submit" className={styles.primaryButton} disabled={submitting}>{submitting ? "Creating record…" : `Create ${config.label} Record`}</button></footer>
            </form>

            <aside className={styles.sidePanel} aria-label="Registration guidance">
              <div className={styles.guideCard}><span className={styles.guideIcon}><ShieldCheckIcon aria-hidden="true" /></span><h2>Secure by design</h2><p>Adding a master record does not create a usable password or activate an account.</p><ol><li><span>1</span><div><strong>Master record created</strong><small>Institutional identity and contact are stored securely.</small></div></li><li><span>2</span><div><strong>{config.label} completes registration</strong><small>The {kind === "student" ? "roll number" : "employee code"} is verified before account access.</small></div></li><li><span>3</span><div><strong>Account becomes active</strong><small>Verified contact and password enable secure sign-in.</small></div></li></ol></div>
              <div className={styles.helperCard}><BuildingLibraryIcon aria-hidden="true" /><div><strong>Managing several records?</strong><p>Use bulk upload from {config.listLabel} to import a completed SYS template.</p><Link href={config.listHref}>Open {config.listLabel} <ArrowLeftIcon aria-hidden="true" /></Link></div></div>
              <p className={styles.securityNote}><CheckCircleIcon aria-hidden="true" /> Administrator actions are recorded in the SYS audit trail.</p>
            </aside>
          </div>
        </main>
      </AdminShell>
    </>
  );
}
