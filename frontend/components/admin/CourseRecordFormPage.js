import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { ArrowLeftIcon, CheckCircleIcon } from "@heroicons/react/24/outline";
import { createCourse, getAdminOperationsSummary, getApiErrorMessage, getCourse, updateCourse } from "../../src/api";
import { COURSE_CATEGORIES, COURSE_SETUP_PHASES, courseFormValues, coursePayload, isExaminationCourse, validateCourseForm } from "../../src/courseMaster";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./CourseMasterWorkspace.module.css";

function Field({ id, label, required = false, hint, full = false, children, ...props }) {
  return <label htmlFor={id} className={`${styles.field} ${full ? styles.full : ""}`}><span>{label}{required ? " *" : ""}</span>{children || <input id={id} name={id} required={required} {...props} />}{hint && <small>{hint}</small>}</label>;
}

export default function CourseRecordFormPage({ mode = "create" }) {
  const router = useRouter();
  const access = useAdminAccess();
  const editing = mode === "edit";
  const [form, setForm] = useState(() => ({ ...courseFormValues(), self_enrollment_enabled: false }));
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    getAdminOperationsSummary({ signal: controller.signal }).then(({ data }) => setSummary(data || null)).catch(() => {});
    return () => controller.abort();
  }, [access.status]);

  useEffect(() => {
    if (!editing || access.status !== "ready" || !router.isReady || !router.query.id) return;
    let active = true;
    setLoading(true);
    getCourse(router.query.id).then(({ data }) => { if (active) setForm({ ...courseFormValues(data), self_enrollment_enabled: Boolean(data.self_enrollment_enabled) }); }).catch((requestError) => { if (active) setError(getApiErrorMessage(requestError, "Unable to load this course.")); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [access.status, editing, router.isReady, router.query.id]);

  function change(event) {
    const { name, value, type, checked } = event.target;
    setForm((previous) => ({ ...previous, [name]: type === "checkbox" ? checked : name === "programme_code" ? value.toUpperCase() : name === "is_active" ? value === "active" : value }));
  }

  async function submit(event) {
    event.preventDefault();
    const validation = validateCourseForm(form);
    if (validation) { setError(validation); return; }
    setError("");
    setSaving(true);
    try {
      const payload = { ...coursePayload(form), self_enrollment_enabled: Boolean(form.self_enrollment_enabled) };
      const response = editing ? await updateCourse(router.query.id, payload) : await createCourse(payload);
      await router.push(`/admin/courses/${response?.data?.id || router.query.id}`);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, `Unable to ${editing ? "update" : "create"} the course.`));
    } finally {
      setSaving(false);
    }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the secure SYS course workspace." />;
  if (access.status === "error") return <BrandedState type="error" title="Course workspace unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  const examination = isExaminationCourse(form.programme_category);
  const title = editing ? "Edit Course" : "Create Course";

  return <>
    <Head><title>{title} | SYS</title><meta name="description" content="Create and maintain an official SYS course master record." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
    <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="Academic Management" pageTitle={title} scopeLabel={summary?.scope_label || "Platform-wide"}>
      <main className={styles.workspace}><Link href={editing && router.query.id ? `/admin/courses/${router.query.id}` : "/admin/courses"} className={styles.back}><ArrowLeftIcon />Back to {editing ? "course profile" : "Course Master"}</Link><header className={styles.heading}><div><span className={styles.eyebrow}>Academic management · Course foundation</span><h1>{title}</h1><p>{editing ? "Update official course details without disrupting the agreed academic setup workflow." : "Establish the official course identity before adding syllabus, academic ownership, and weightages."}</p></div></header>

        <div className={styles.formLayout}><form className={styles.formCard} onSubmit={submit} noValidate>{error && <div className={styles.error} role="alert">{error}</div>}{loading ? <div className={styles.loading}>Loading course information…</div> : <>
          <section className={styles.section}><h2>Course identity</h2><p>Create a clear institutional identity that students and faculty can recognize.</p><div className={styles.fieldGrid}><Field id="title" label="Course title" value={form.title} onChange={change} placeholder="For example, NEET Preparation" required /><Field id="programme_code" label="Course code" value={form.programme_code} onChange={change} placeholder="For example, NEET-2027" hint="Unique code; letters, numbers, hyphens, and underscores only." required /><Field id="programme_category" label="Course category" required><select id="programme_category" name="programme_category" value={form.programme_category} onChange={change}>{COURSE_CATEGORIES.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</select></Field><Field id="is_active" label="Publication status"><select id="is_active" name="is_active" value={form.is_active ? "active" : "draft"} onChange={change}><option value="draft">Draft — hidden from the student catalogue</option><option value="active">Active — available in the student catalogue</option></select></Field><Field id="description" label="Course description" full><textarea id="description" name="description" value={form.description} onChange={change} placeholder="Describe the course, intended learners, and expected academic coverage." /></Field></div></section>

          <section className={styles.section}><h2>{examination ? "Examination and learning objective" : "Learning objective"}</h2><p>{examination ? "Record the examination identity and organizing authority." : "Define what the learner should achieve through this course."}</p><div className={styles.fieldGrid}>{examination && <><Field id="examination_name" label="Examination name" value={form.examination_name} onChange={change} placeholder="For example, NEET" required /><Field id="examination_authority" label="Examination authority" value={form.examination_authority} onChange={change} placeholder="For example, the responsible examination authority" /></>}<Field id="target_purpose" label="Target purpose and learning outcome" full><textarea id="target_purpose" name="target_purpose" value={form.target_purpose} onChange={change} placeholder={examination ? "Describe the examination-preparation outcome and intended learner group." : "Describe the skills, capabilities, or academic outcomes students should develop."} /></Field></div></section>

          <section className={styles.section}>
            <h2>Enrollment policy</h2>
            <p>Administrator enrollment remains available. Enable self-enrollment only when eligible students may join this published course directly.</p>
            <div className={styles.enrollmentPolicy}>
              <label className={styles.enrollmentToggle} htmlFor="self_enrollment_enabled">
                <input id="self_enrollment_enabled" name="self_enrollment_enabled" type="checkbox" checked={Boolean(form.self_enrollment_enabled)} onChange={change} aria-describedby="self-enrollment-help" />
                <span>Student self-enrollment</span>
              </label>
              <p id="self-enrollment-help" className={styles.enrollmentHelp}>Allow eligible students to enroll themselves after publication. Leave unchecked for administrator-managed enrollment.</p>
            </div>
          </section>

          <section className={styles.section}><h2>Reference documents</h2><p>Add approved external references when they are available.</p><div className={styles.fieldGrid}><Field id="syllabus_url" label="Official syllabus reference URL" type="url" value={form.syllabus_url} onChange={change} placeholder="https://example.org/official-syllabus" hint="Reference document only. Structured syllabus authoring belongs to the next phase." /><Field id="resources_url" label="Learning resources URL" type="url" value={form.resources_url} onChange={change} placeholder="https://example.org/course-resources" hint="Optional institution-approved resources or reference material." /></div></section>

          <section className={styles.section}><div className={styles.notice}><strong>What happens after the course is created?</strong><br />The next phase introduces structured syllabus setup: Course → Subject → Unit → Topic → Subtopic. Faculty ownership and academic weightages follow in their approved implementation phases.</div></section>
          <div className={styles.formActions}><Link href={editing && router.query.id ? `/admin/courses/${router.query.id}` : "/admin/courses"} className={styles.button}>Cancel</Link><button type="submit" className={styles.buttonPrimary} disabled={saving}><CheckCircleIcon />{saving ? "Saving…" : editing ? "Save changes" : "Create course"}</button></div>
        </>}</form>

        <aside className={styles.sideCard}><h2>Academic setup roadmap</h2><p>SYS courses are established through five controlled implementation phases.</p><div className={styles.phases}>{COURSE_SETUP_PHASES.map((phase, index) => <div className={styles.phase} key={phase.title}><span className={styles.phaseNumber}>{index + 1}</span><div><strong>{phase.title}{index === 0 ? " · Current phase" : ""}</strong><small>{phase.description}</small></div></div>)}</div></aside></div>
      </main>
    </AdminShell>
  </>;
}
