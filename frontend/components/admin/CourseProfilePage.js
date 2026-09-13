import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { ArrowDownTrayIcon, ArrowLeftIcon, BookOpenIcon, PencilSquareIcon, UserGroupIcon } from "@heroicons/react/24/outline";
import { adminListSubjectExperts, downloadCourseProfilePdf, downloadCourseSyllabusPdf, downloadSubjectProfilePdf, downloadSubjectSyllabusPdf, getAdminOperationsSummary, getApiErrorMessage, getCourse, getCourseAcademicWeightages, getCoursePublicationReadiness, submitCourseForReview, publishCourse, returnCourseToDraft, archiveCourse } from "../../src/api";
import { courseCategoryLabel, courseDateLabel, courseReadiness, courseStatusLabel } from "../../src/courseMaster";
import { weightageReadiness } from "../../src/academicWeightages";
import { downloadBlob } from "../../src/adminMaster";
import API from "../../src/api";
import { configurationLabel } from "../../src/syllabusConfiguration";
import { courseReportFilename, subjectReportRows } from "../../src/courseReports";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import PilotPublicationCard from "./PilotPublicationCard";
import useAdminAccess from "./useAdminAccess";
import styles from "./CourseMasterWorkspace.module.css";

function Fact({ label, value, href }) {
  let safeHref = null;
  if (href) {
    try { const parsed = new URL(href); if (["http:", "https:"].includes(parsed.protocol)) safeHref = parsed.href; } catch {}
  }
  return <div className={styles.fact}><span>{label}</span><strong>{safeHref ? <a href={safeHref} target="_blank" rel="noopener noreferrer">Open approved reference</a> : value || "Not available"}</strong></div>;
}

function Card({ title, description, wide = false, children }) {
  return <section className={`${styles.detailCard} ${wide ? styles.detailCardWide : ""}`}><h2>{title}</h2><p>{description}</p>{children}</section>;
}

export default function CourseProfilePage() {
  const router = useRouter();
  const access = useAdminAccess();
  const [course, setCourse] = useState(null);
  const [summary, setSummary] = useState(null);
  const [subjectExperts, setSubjectExperts] = useState([]);
  const [weightages, setWeightages] = useState(null);
  const [publication, setPublication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [reportDownloading, setReportDownloading] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    getAdminOperationsSummary({ signal: controller.signal }).then(({ data }) => setSummary(data || null)).catch(() => {});
    return () => controller.abort();
  }, [access.status]);

  useEffect(() => {
    if (access.status !== "ready" || !router.isReady || !router.query.id) return;
    let active = true;
    setLoading(true);
    Promise.all([getCourse(router.query.id), adminListSubjectExperts()]).then(([courseResponse, expertResponse]) => { if (active) { setCourse(courseResponse.data); setSubjectExperts(courseResponse.data.syllabus_configuration?.experts || (Array.isArray(expertResponse.data) ? expertResponse.data.filter((assignment) => String(assignment.course_id) === String(router.query.id)) : [])); } }).catch((requestError) => { if (active) setError(getApiErrorMessage(requestError, "Unable to load the course profile.")); }).finally(() => { if (active) setLoading(false); });
    getCourseAcademicWeightages(router.query.id).then(({ data }) => { if (active) setWeightages(data); }).catch(() => {});
    getCoursePublicationReadiness(router.query.id).then(({ data }) => { if (active) setPublication(data); }).catch(() => {});
    return () => { active = false; };
  }, [access.status, router.isReady, router.query.id]);

  async function changeStatus(action) {
    if (!course || updating) return;
    const pendingCount = publication?.pending_enrollment_count || 0;
    const confirmation = action === "publish" ? `Publish this course and activate ${pendingCount} pending assignments? Ineligible students will remain pending and be reported.` : "Confirm the selected course publication action?";
    if (!window.confirm(confirmation)) return;
    setUpdating(true);
    setError("");
    try { const handlers = { review: submitCourseForReview, publish: publishCourse, draft: returnCourseToDraft, archive: archiveCourse }; const { data } = await handlers[action](course.id, action === "publish" ? { activate_pending: true, expected_pending_count: pendingCount } : undefined); setPublication(data); if (action === "publish") window.alert(`Course published. ${data.enrollment_activation?.activated || 0} assignments activated; ${data.enrollment_activation?.skipped || 0} ineligible students remain pending. Review Manage enrollments for details.`); const refreshed = await getCourse(course.id); setCourse(refreshed.data); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to update the course status.")); }
    finally { setUpdating(false); }
  }

  async function downloadReport(type, subject = null) {
    if (!course || reportDownloading) return;
    const key = `${type}-${subject?.subject_id || "course"}`;
    setReportDownloading(key); setError("");
    try {
      const response = subject?.draft_review_id ? await API.get(`/courses/${course.id}/syllabus-review/reviews/${subject.draft_review_id}/syllabus.pdf`, { params: { subject_key: subject.subject_key }, responseType: "blob" }) : subject ? await (type === "syllabus" ? downloadSubjectSyllabusPdf(course.id, subject.subject_id) : downloadSubjectProfilePdf(course.id, subject.subject_id)) : await (type === "syllabus" ? downloadCourseSyllabusPdf(course.id) : downloadCourseProfilePdf(course.id));
      downloadBlob(response.data, courseReportFilename(response, { scope: subject ? "Subject" : "Course", type: type === "syllabus" ? "Syllabus" : "Profile", identifier: subject?.subject_name || course.programme_code || course.title }));
    } catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to download the requested academic report.")); }
    finally { setReportDownloading(""); }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the secure SYS course profile." />;
  if (access.status === "error") return <BrandedState type="error" title="Course profile unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  const coordinators = course?.course_coordinators || [];

  return <>
    <Head><title>{course?.title || "Course Profile"} | SYS</title><meta name="description" content="SYS course identity, academic readiness, faculty, learning, and enrollment profile." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
    <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="Academic Management" pageTitle="Course Profile" scopeLabel={summary?.scope_label || "Platform-wide"}>
      <main className={styles.workspace}><Link href="/admin/courses" className={styles.back}><ArrowLeftIcon />Back to Course Master</Link>{error && <div className={styles.error} role="alert">{error}</div>}{loading ? <div className={styles.loading}>Loading the current course profile…</div> : !course ? <div className={styles.empty}><h3>Course profile unavailable</h3><p>The requested course could not be loaded.</p></div> : <>
        <section className={styles.hero}><div><span className={styles.eyebrow}>SYS institutional course profile</span><h1>{course.title}</h1><p>Course code: {course.programme_code || "Not configured"}</p><div className={styles.heroMeta}><span className={styles.heroTag}>{courseCategoryLabel(course.programme_category)}</span><span className={course.is_active ? styles.statusActive : styles.statusDraft}>{courseStatusLabel(course)}</span>{course.examination_name && <span className={styles.heroTag}>{course.examination_name}</span>}</div></div><div className={styles.heroActions}><button type="button" className={styles.button} onClick={() => downloadReport("profile")} disabled={Boolean(reportDownloading)}><ArrowDownTrayIcon />{reportDownloading === "profile-course" ? "Preparing course PDF…" : "Download course profile PDF"}</button><button type="button" className={styles.buttonLight} onClick={() => downloadReport("syllabus")} disabled={Boolean(reportDownloading)}><ArrowDownTrayIcon />{reportDownloading === "syllabus-course" ? "Preparing syllabus PDF…" : "Download syllabus PDF"}</button><Link href={`/admin/courses/${course.id}/syllabus`} className={styles.buttonLight}><BookOpenIcon />Manage syllabus</Link><Link href={`/admin/courses/${course.id}/edit`} className={styles.buttonLight}><PencilSquareIcon />Edit course</Link><Link href={`/admin/courses/${course.id}/enrollments`} className={styles.buttonLight}><UserGroupIcon />Manage enrollments</Link><a href="#publication-readiness" className={styles.buttonLight}>Publication readiness</a></div></section>

        {course.syllabus_configuration && <div className={styles.notice}>{configurationLabel(course.syllabus_configuration)}</div>}
        <section className={styles.metrics} aria-label="Course activity"><article className={styles.metric}><span>Subjects configured</span><strong>{course.subject_count || 0}</strong><small>{course.unit_count || 0} units · {course.topic_count || 0} topics · {course.subtopic_count || 0} subtopics</small></article><article className={styles.metric}><span>Enrolled students</span><strong>{course.student_count || 0}</strong><small>Verified course enrollments</small></article><article className={styles.metric}><span>Academic faculty</span><strong>{coordinators.length + Number(course.subject_expert_count || 0)}</strong><small>{coordinators.length} coordinators · {course.subject_expert_count || 0} subject experts</small></article><article className={styles.metric}><span>Assessments</span><strong>{course.assessment_count || 0}</strong><small>{course.question_count || 0} questions · {course.learning_session_count || 0} learning sessions</small></article></section>

        <div className={styles.detailGrid}><Card title="Course identity and examination" description="Official academic identity, examination details, and intended outcome."><div className={styles.facts}><Fact label="Course title" value={course.title} /><Fact label="Course code" value={course.programme_code} /><Fact label="Course category" value={courseCategoryLabel(course.programme_category)} /><Fact label="Publication status" value={courseStatusLabel(course)} /><Fact label="Examination name" value={course.examination_name || "Not applicable or not configured"} /><Fact label="Examination authority" value={course.examination_authority || "Not configured"} /><Fact label="Learning objective" value={course.target_purpose || "Learning objective has not been added yet."} /><Fact label="Course description" value={course.description || "Course description has not been added yet."} /></div></Card>

        <Card title="Academic syllabus and reference material" description="Current verified academic structure and approved reference documents."><div className={styles.facts}><Fact label="Subjects" value={`${course.subject_count || 0} configured`} /><Fact label="Units" value={`${course.unit_count || 0} configured`} /><Fact label="Topics" value={`${course.topic_count || 0} configured`} /><Fact label="Subtopics" value={`${course.subtopic_count || 0} configured`} /><Fact label="Syllabus readiness" value={course.subject_count ? "Academic subjects are available" : "No subjects configured yet"} /><Fact label="Official syllabus reference" value="No syllabus reference added yet" href={course.syllabus_url} /><Fact label="Learning resources" value="No learning resources added yet" href={course.resources_url} /></div><div className={styles.notice} style={{ marginTop: 16 }}>Manage the complete structured hierarchy: Course → Subject → Unit → Topic → Subtopic. <Link href={`/admin/courses/${course.id}/syllabus`}>Open syllabus workspace</Link></div></Card>

        <Card title="Faculty and academic responsibilities" description="Verified course-coordinator assignments and subject-expert ownership.">{coordinators.length ? <div className={styles.list}>{coordinators.map((person, index) => <div className={styles.person} key={person.id || person.faculty_id || index}><Link href={`/admin/faculty/${person.faculty_id}`}><strong>{person.faculty_name || "Faculty coordinator"}</strong></Link><small>{person.faculty_email || person.faculty_employee_code || "Course coordinator"}</small></div>)}</div> : <div className={styles.notice}>No course coordinator assigned yet.</div>}{subjectExperts.length ? <div className={styles.list}>{subjectExperts.map((person) => <div className={styles.person} key={`expert-${person.id}`}><Link href={`/admin/faculty/${person.faculty_id}`}><strong>{person.faculty_name}</strong></Link><small>{person.subject_name} · Subject expert</small></div>)}</div> : <div className={styles.notice}>No subject experts assigned yet.</div>}{subjectReportRows(subjectExperts).length > 0 && <div className={styles.list}>{subjectReportRows(subjectExperts).map((subject) => <div className={styles.person} key={`subject-report-${subject.subject_id}`}><strong>{subject.subject_name} reports</strong><div className={styles.actions} style={{ marginTop: 8 }}>{!subject.draft_review_id && <button type="button" className={styles.button} disabled={Boolean(reportDownloading)} onClick={() => downloadReport("profile", subject)}><ArrowDownTrayIcon />Subject profile PDF</button>}<button type="button" className={styles.button} disabled={Boolean(reportDownloading)} onClick={() => downloadReport("syllabus", subject)}><ArrowDownTrayIcon />Subject syllabus PDF</button></div></div>)}</div>}<div className={styles.facts}><Fact label="Course coordinators" value={`${coordinators.length} assigned`} /><Fact label="Subject experts" value={`${course.subject_expert_count || 0} assigned`} /></div><div className={styles.notice}><Link href={`/admin/academic-responsibilities?course_id=${course.id}`}>Manage academic responsibilities</Link></div></Card>

        <Card title="Students and learning activity" description="Course enrollments and verified learning engagement."><div className={styles.facts}><Fact label="Student enrollments" value={course.student_count ? `${course.student_count} students enrolled` : "No students enrolled yet"} /><Fact label="Learning sessions" value={course.learning_session_count ? `${course.learning_session_count} sessions recorded` : "Learning has not started yet"} /><Fact label="Assessments" value={course.assessment_count ? `${course.assessment_count} assessments created` : "No assessments created yet"} /><Fact label="Question bank" value={course.question_count ? `${course.question_count} questions available` : "No questions created yet"} /></div></Card>

        <Card title="Academic weightage and prioritization" description="Approved subject, unit, topic, and subtopic importance for learning and examination intelligence."><div className={styles.facts}><Fact label="Subject weightages" value={`${weightages?.configured?.subjects || 0} configured`} /><Fact label="Unit weightages" value={`${weightages?.configured?.units || 0} configured`} /><Fact label="Topic weightages" value={`${weightages?.configured?.topics || 0} configured`} /><Fact label="Subtopic weightages" value={`${weightages?.configured?.subtopics || 0} configured`} /><Fact label="Academic readiness" value={`${weightageReadiness(weightages).percent}% complete`} /></div><div className={styles.notice}>{weightageReadiness(weightages).completed ? `${weightageReadiness(weightages).completed} academic weightage groups configured.` : "Academic weightages have not been configured yet."} <Link href={`/admin/courses/${course.id}/weightages`}>Manage academic weightages</Link></div></Card>

        <Card title="Record activity" description="Current course record history and publication state."><div className={styles.facts}><Fact label="Course created" value={courseDateLabel(course.created_at)} /><Fact label="Last updated" value={courseDateLabel(course.updated_at)} /><Fact label="Catalogue availability" value={course.is_active ? "Available to eligible students" : "Not visible while the course is a draft"} /><Fact label="Administrator access" value="Restricted to authorized SYS administrators" /></div></Card>

        <PilotPublicationCard course={course} onPublished={() => router.reload()} />

        <div id="publication-readiness" style={{ display: "contents" }}><Card title="Course publication readiness" description={publication?.ready ? "All mandatory academic publication requirements are complete." : "Complete every mandatory academic requirement before publishing this course."} wide><div className={styles.readiness}>{(publication?.checks || courseReadiness(course)).map((item) => <div className={styles.readyItem} key={item.label}><div><strong>{item.label}</strong><small>{item.href && !item.complete ? <Link href={item.href}>{item.detail}</Link> : item.detail}</small></div><span className={item.complete ? styles.readyYes : styles.readyNo}>{item.complete ? "Complete" : "Needs attention"}</span></div>)}</div><div className={styles.actions} style={{ marginTop: 20 }}>{course.publication_status === "DRAFT" && <button className={styles.button} onClick={() => changeStatus("review")} disabled={updating || !publication?.ready}>Submit for review</button>}{course.publication_status === "READY_FOR_REVIEW" && <button className={styles.button} onClick={() => changeStatus("publish")} disabled={updating || !publication?.ready}>Publish course</button>}{course.publication_status === "PUBLISHED" && <button className={styles.button} onClick={() => changeStatus("draft")} disabled={updating}>Return to draft</button>}{course.publication_status !== "ARCHIVED" && <button className={styles.button} onClick={() => changeStatus("archive")} disabled={updating}>Archive course</button>}</div></Card></div></div>
      </>}</main>
    </AdminShell>
  </>;
}
