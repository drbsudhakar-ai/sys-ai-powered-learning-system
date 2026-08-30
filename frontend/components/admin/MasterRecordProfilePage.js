import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";
import { AcademicCapIcon, ArrowDownTrayIcon, ArrowLeftIcon, BriefcaseIcon, CheckBadgeIcon, ClockIcon, IdentificationIcon, PencilSquareIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import {
  adminActivateFaculty, adminActivateStudent, adminAssignCourseCoordinator, adminAssignSubjectExpert,
  adminCreateSubject, adminDeactivateFaculty, adminDeactivateStudent, adminDownloadFacultyMasterProfile,
  adminDownloadStudentMasterProfile, adminGetFaculty, adminGetFacultyMasterProfile, adminGetStudentMasterProfile,
  adminListSubjects, adminRemoveCourseCoordinator, adminRemoveSubjectExpert, getAdminOperationsSummary,
  getApiErrorMessage, getCourses,
} from "../../src/api";
import { downloadBlob } from "../../src/adminMaster";
import { profileDateLabel, profileDownloadFilename, profileInitials, profilePhotoUrl, profileStatusLabel } from "../../src/masterProfile";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./MasterRecordProfilePage.module.css";

const CONFIG = {
  student: { label: "Student", listHref: "/admin/students", identifier: "roll_number", identifierLabel: "Roll number", getProfile: adminGetStudentMasterProfile, download: adminDownloadStudentMasterProfile, activate: adminActivateStudent, deactivate: adminDeactivateStudent },
  faculty: { label: "Faculty", listHref: "/admin/faculty", identifier: "employee_code", identifierLabel: "Employee code", getProfile: adminGetFacultyMasterProfile, download: adminDownloadFacultyMasterProfile, activate: adminActivateFaculty, deactivate: adminDeactivateFaculty },
};

function DetailCard({ icon: Icon, title, description, children, wide = false }) {
  return <section className={`${styles.detailCard} ${wide ? styles.wideCard : ""}`}><div className={styles.sectionHeading}><span className={styles.sectionIcon}><Icon aria-hidden="true" /></span><div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>{children}</section>;
}

function Details({ fields }) {
  return <dl className={styles.detailGrid}>{fields.map(({ label, value, wide, tone }) => <div key={label} className={wide ? styles.fullWidth : undefined}><dt>{label}</dt><dd className={tone === "success" ? styles.verifiedValue : tone === "warning" ? styles.pendingValue : undefined}>{value ?? "Not available"}</dd></div>)}</dl>;
}

function ActivityCard({ icon, title, description, fields, active, emptyMessage, items = [] }) {
  return <DetailCard icon={icon} title={title} description={description}>
    <Details fields={fields} />
    {!active && <p className={styles.activityEmpty}>{emptyMessage}</p>}
    {active && items.length > 0 && <div className={styles.activityList}>{items.slice(0, 3).map((item, index) => <div key={`${item.title || item.name}-${index}`}><strong>{item.title || item.name}</strong><span>{item.percentage == null ? profileStatusLabel(item.status || item.classification || item.mode) : `${item.percentage}% · ${profileStatusLabel(item.status)}`}</span></div>)}</div>}
  </DetailCard>;
}

function percentageLabel(value) {
  return value == null ? "Not assessed yet" : `${value}%`;
}

function StudentActivitySections({ profile, record }) {
  const activity = profile?.activity || {};
  const learning = activity.learning || {};
  const assessments = activity.assessments || {};
  const performance = activity.performance || {};
  const remediation = activity.remediation || {};
  const mastery = activity.mastery || {};
  const journey = activity.journey || {};
  const support = activity.support || {};
  const notifications = activity.notifications || {};
  const communicationCourses = (record.programmes || []).filter((course) => /english|communication|spoken/i.test(course.title || ""));

  return <>
    <ActivityCard icon={ClockIcon} title="Learning sessions and progress" description="Participation in individual, common, and hybrid learning sessions." active={learning.total > 0} emptyMessage="Learning has not started yet. Session activity will appear after the student joins a learning session." fields={[{ label: "Sessions attended", value: learning.total || 0 }, { label: "Completed sessions", value: learning.completed || 0 }, { label: "Currently in progress", value: learning.in_progress || 0 }]} items={learning.recent || []} />
    <ActivityCard icon={AcademicCapIcon} title="Assessment performance" description="Assessment attempts, completion, scores, and recent results." active={assessments.attempted > 0} emptyMessage="No assessments attempted yet. Performance will appear after the first assessment." fields={[{ label: "Assessments attempted", value: assessments.attempted || 0 }, { label: "Completed", value: assessments.completed || 0 }, { label: "Average score", value: percentageLabel(assessments.average_percentage) }, { label: "Best score", value: percentageLabel(assessments.best_percentage) }]} items={assessments.recent || []} />
    <ActivityCard icon={IdentificationIcon} title="Performance analysis and learning gaps" description="Observed academic trends, readiness, and identified improvement areas." active={(performance.analyses || 0) > 0 || (performance.learning_gaps || 0) > 0} emptyMessage="Performance analysis has not started yet. Learning gaps appear after assessment evaluation." fields={[{ label: "Performance analyses", value: performance.analyses || 0 }, { label: "Identified learning gaps", value: performance.learning_gaps || 0 }, { label: "High-priority gaps", value: performance.high_priority_gaps || 0 }, { label: "Performance trend", value: performance.trend ? profileStatusLabel(performance.trend) : "Not available yet" }]} items={performance.areas || []} />
    <ActivityCard icon={BriefcaseIcon} title="Remedial learning and interventions" description="Targeted remedial groups, interventions, and reassessment requirements." active={(remediation.groups || 0) > 0 || (remediation.interventions || 0) > 0} emptyMessage="No remedial support assigned yet. Interventions are created when learning gaps require attention." fields={[{ label: "Remedial groups", value: remediation.groups || 0 }, { label: "Interventions assigned", value: remediation.interventions || 0 }, { label: "Active interventions", value: remediation.active || 0 }, { label: "Completed", value: remediation.completed || 0 }, { label: "Pending reassessments", value: remediation.reassessments_pending || 0 }]} />
    <ActivityCard icon={CheckBadgeIcon} title="Topic mastery and adaptive practice" description="Topic-level mastery, adaptive practice assignments, and progress." active={(mastery.topics || 0) > 0 || (mastery.practice_assigned || 0) > 0} emptyMessage="Mastery tracking has not started yet. Topic progress appears after learning and assessment activity." fields={[{ label: "Topics tracked", value: mastery.topics || 0 }, { label: "Topics mastered", value: mastery.mastered || 0 }, { label: "Average mastery", value: percentageLabel(mastery.average_mastery) }, { label: "Practice assignments", value: mastery.practice_assigned || 0 }, { label: "Practice completed", value: mastery.practice_completed || 0 }]} />
    <ActivityCard icon={ClockIcon} title="Learning journey and next action" description="Personalized recommendations and the next appropriate learning action." active={(journey.total_actions || 0) > 0} emptyMessage="The learning journey has not started yet. Recommendations appear after course enrollment and learning activity." fields={[{ label: "Recommended actions", value: journey.total_actions || 0 }, { label: "Pending actions", value: journey.pending_actions || 0 }, { label: "Completed actions", value: journey.completed_actions || 0 }, { label: "Next recommended action", value: journey.next_action || "No action recommended yet", wide: true }]} />
    <ActivityCard icon={ShieldCheckIcon} title="Early warnings and student support" description="Observed learning risks, pending interventions, and actions requiring attention." active={(support.high_priority_gaps || 0) > 0 || (support.pending_remediation || 0) > 0 || (support.pending_journey_actions || 0) > 0} emptyMessage="No academic warnings or support interventions have been identified yet." fields={[{ label: "High-priority learning gaps", value: support.high_priority_gaps || 0 }, { label: "Active remedial support", value: support.pending_remediation || 0 }, { label: "Pending learning actions", value: support.pending_journey_actions || 0 }, { label: "Unread notifications", value: support.unread_notifications || 0 }]} />
    <ActivityCard icon={AcademicCapIcon} title="English communication and skill development" description="Enrollment and participation in independent communication-skills programmes." active={communicationCourses.length > 0} emptyMessage="Not registered for an English communication programme yet." fields={[{ label: "Communication programmes", value: communicationCourses.length }, { label: "Enrollment status", value: communicationCourses.length ? "Enrolled" : "Not registered yet" }]} items={communicationCourses.map((course) => ({ title: course.title, status: "ENROLLED" }))} />
    <ActivityCard icon={IdentificationIcon} title="Notifications and engagement" description="Institutional notifications and recorded student engagement." active={(notifications.total || 0) > 0} emptyMessage="No notifications or engagement activity recorded yet." fields={[{ label: "Notifications received", value: notifications.total || 0 }, { label: "Unread notifications", value: notifications.unread || 0 }]} items={notifications.recent || []} />
  </>;
}

function FacultyActivitySections({ profile }) {
  const activity = profile?.activity || {};
  const teaching = activity.teaching || {};
  const assessments = activity.assessments || {};
  const oversight = activity.oversight || {};
  const remediation = activity.remediation || {};
  const content = activity.content || {};
  const notifications = activity.notifications || {};

  return <>
    <ActivityCard icon={AcademicCapIcon} title="Teaching and learning sessions" description="Faculty-created or facilitated individual, common, and hybrid learning sessions." active={(teaching.total || 0) > 0} emptyMessage="No teaching or facilitated learning sessions have started yet." fields={[{ label: "Sessions facilitated", value: teaching.total || 0 }, { label: "Completed sessions", value: teaching.completed || 0 }, { label: "Currently in progress", value: teaching.in_progress || 0 }]} items={teaching.recent || []} />
    <ActivityCard icon={CheckBadgeIcon} title="Assessment creation and evaluation" description="Assessments authored by the faculty member and corresponding student attempts." active={(assessments.created || 0) > 0} emptyMessage="No assessments have been created or assigned by this faculty member yet." fields={[{ label: "Assessments created", value: assessments.created || 0 }, { label: "Published assessments", value: assessments.published || 0 }, { label: "Draft assessments", value: assessments.draft || 0 }, { label: "Student attempts", value: assessments.student_attempts || 0 }]} items={assessments.recent || []} />
    <ActivityCard icon={IdentificationIcon} title="Student performance and academic oversight" description="Enrolled students and learning-gap indicators within coordinated SYS courses." active={(oversight.coordinator_courses || 0) > 0} emptyMessage="No course coordination or student academic oversight has been assigned yet." fields={[{ label: "Coordinated courses", value: oversight.coordinator_courses || 0 }, { label: "Students under coordination", value: oversight.students || 0 }, { label: "Identified learning gaps", value: oversight.learning_gaps || 0 }, { label: "High-priority gaps", value: oversight.high_priority_gaps || 0 }]} />
    <ActivityCard icon={ShieldCheckIcon} title="Remedial guidance and interventions" description="Remedial groups and targeted academic interventions created by this faculty member." active={(remediation.groups_created || 0) > 0 || (remediation.interventions_created || 0) > 0} emptyMessage="No remedial groups or student interventions have been created yet." fields={[{ label: "Remedial groups created", value: remediation.groups_created || 0 }, { label: "Interventions created", value: remediation.interventions_created || 0 }, { label: "Active interventions", value: remediation.active || 0 }, { label: "Completed interventions", value: remediation.completed || 0 }]} />
    <ActivityCard icon={BriefcaseIcon} title="Question bank and academic content" description="Verified question-bank contributions and SYS courses authored by the faculty member." active={(content.questions_created || 0) > 0 || (content.courses_created || 0) > 0} emptyMessage="No question-bank items or academic course content have been created yet." fields={[{ label: "Questions created", value: content.questions_created || 0 }, { label: "SYS courses created", value: content.courses_created || 0 }]} />
    <ActivityCard icon={ClockIcon} title="Communication and notifications" description="Official notifications and faculty communication activity recorded in SYS." active={(notifications.total || 0) > 0} emptyMessage="No faculty notifications or communication activity recorded yet." fields={[{ label: "Notifications received", value: notifications.total || 0 }, { label: "Unread notifications", value: notifications.unread || 0 }]} items={notifications.recent || []} />
  </>;
}

export default function MasterRecordProfilePage({ kind }) {
  const config = CONFIG[kind];
  const router = useRouter();
  const access = useAdminAccess();
  const id = router.query.id;
  const [profile, setProfile] = useState(null);
  const [facultyDetails, setFacultyDetails] = useState(null);
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [working, setWorking] = useState(false);
  const [photoFailed, setPhotoFailed] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [courseId, setCourseId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [newSubjectName, setNewSubjectName] = useState("");

  const refresh = useCallback(async () => {
    if (!id) return;
    if (kind === "faculty") {
      const [profileResponse, facultyResponse, courseResponse, subjectResponse] = await Promise.all([config.getProfile(id), adminGetFaculty(id), getCourses(), adminListSubjects()]);
      setProfile(profileResponse.data);
      setFacultyDetails(facultyResponse.data);
      setCourses(Array.isArray(courseResponse.data) ? courseResponse.data : []);
      setSubjects(Array.isArray(subjectResponse.data) ? subjectResponse.data : []);
    } else {
      const response = await config.getProfile(id);
      setProfile(response.data);
    }
  }, [config, id, kind]);

  useEffect(() => {
    if (access.status !== "ready" || !router.isReady || !id) return undefined;
    let current = true;
    setLoading(true);
    setError("");
    refresh().catch((requestError) => { if (current) setError(getApiErrorMessage(requestError, `Unable to load the ${config.label.toLowerCase()} profile.`)); }).finally(() => { if (current) setLoading(false); });
    getAdminOperationsSummary().then((response) => { if (current) setSummary(response.data || null); }).catch(() => {});
    return () => { current = false; };
  }, [access.status, config.label, id, refresh, router.isReady]);

  useEffect(() => { setPhotoFailed(false); }, [profile?.record?.photo_url]);

  async function perform(action, message) {
    setWorking(true); setError(""); setNotice("");
    try { await action(); await refresh(); setNotice(message); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to update this profile.")); }
    finally { setWorking(false); }
  }

  async function downloadProfile() {
    setDownloading(true); setError("");
    try { const response = await config.download(id); downloadBlob(response.data, profileDownloadFilename(response, kind, profile?.record?.[config.identifier])); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to download the profile PDF.")); }
    finally { setDownloading(false); }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the secure SYS institutional profile." />;
  if (access.status === "error") return <BrandedState type="error" title="Administrator access unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  const record = profile?.record;
  const identifier = record?.[config.identifier];
  const photo = profilePhotoUrl(record, kind);
  const pending = String(record?.registration_status || "").startsWith("PENDING");
  const coordinatorAssignments = facultyDetails?.course_coordinator_assignments || [];
  const expertAssignments = facultyDetails?.subject_expert_assignments || [];

  return <>
    <Head><title>{record ? `${record.name} | ${config.label} Profile | SYS` : `${config.label} Profile | SYS`}</title><meta name="description" content={`Secure SYS ${config.label.toLowerCase()} institutional profile.`} /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
    <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="People & Access" pageTitle={`${config.label} Profile`} scopeLabel={summary?.scope_label || "Platform-wide"}>
      <main className={styles.workspace}>
        <Link href={config.listHref} className={styles.backLink}><ArrowLeftIcon aria-hidden="true" /> Back to {config.label} Master</Link>
        {loading && <div className={styles.loadingState} role="status">Loading {config.label.toLowerCase()} profile...</div>}
        {error && <div className={styles.errorBanner} role="alert">{error}</div>}
        {notice && <div className={styles.noticeBanner} role="status">{notice}</div>}
        {!loading && record && <>
          <section className={styles.profileHero}><div className={styles.heroIdentity}><div className={styles.profileAvatar}>{photo && !photoFailed ? <Image src={photo} alt={`${record.name} profile photograph`} width={88} height={88} unoptimized onError={() => setPhotoFailed(true)} /> : <span aria-label={`${record.name} initials`}>{profileInitials(record.name)}</span>}</div><div className={styles.heroText}><span className={styles.eyebrow}>{config.label} institutional profile</span><h1>{record.name}</h1><p>{config.identifierLabel}: <strong>{identifier || "Not available"}</strong></p><div className={styles.heroBadges}><span className={pending ? styles.pendingBadge : record.is_active ? styles.activeBadge : styles.inactiveBadge}>{profileStatusLabel(record.registration_status)}</span>{record.college && <span className={styles.collegeBadge}>{record.college}</span>}</div></div></div><div className={styles.heroActions}><button type="button" className={styles.downloadButton} onClick={downloadProfile} disabled={downloading}><ArrowDownTrayIcon aria-hidden="true" />{downloading ? "Preparing PDF..." : "Download profile PDF"}</button><Link href={`${config.listHref}/${record.id}/edit`} className={styles.editButton}><PencilSquareIcon aria-hidden="true" /> Edit profile</Link></div></section>

          <div className={styles.profileGrid}>
            <DetailCard icon={IdentificationIcon} title="Identity and contact" description="Official institutional identity and current contact details."><Details fields={[{ label: "Full name", value: record.name }, { label: config.identifierLabel, value: identifier }, { label: "Email address", value: record.email || "Not available", wide: true }, { label: "Mobile number", value: record.mobile_number || "Not available" }, { label: "System role", value: config.label }]} /></DetailCard>
            <DetailCard icon={kind === "student" ? AcademicCapIcon : BriefcaseIcon} title={kind === "student" ? "Academic information" : "Professional information"} description={kind === "student" ? "Institutional degree programme and current academic standing." : "Institution, department, designation, and employment details."}><Details fields={kind === "student" ? [{ label: "College", value: record.college || "Not available", wide: true }, { label: "Academic programme", value: record.academic_program || "Not available", wide: true }, { label: "Admission year", value: record.admission_year ?? "Not available" }, { label: "Present year", value: record.present_year ?? "Not available" }, { label: "Academic status", value: profileStatusLabel(record.academic_status) }] : [{ label: "College", value: record.college || "Not available", wide: true }, { label: "Department", value: record.department || "Not available" }, { label: "Designation", value: record.designation || "Not available" }, { label: "Employment status", value: profileStatusLabel(record.employment_status) }]} /></DetailCard>

            {kind === "student" ? <DetailCard icon={AcademicCapIcon} title="Registered SYS courses" description="Goal-oriented SYS learning programmes, separate from the institutional degree." wide>{record.programmes?.length ? <div className={styles.assignmentList}>{record.programmes.map((programme) => <div key={programme.id} className={styles.assignmentItem}><span><strong>{programme.title}</strong><small>Enrolled SYS programme</small></span><span className={styles.activeBadge}>Enrolled</span></div>)}</div> : <div className={styles.emptyState}>No SYS courses enrolled yet.</div>}</DetailCard> : <DetailCard icon={AcademicCapIcon} title="Academic responsibilities" description="Manage course-coordinator and subject-expert assignments." wide><div className={styles.responsibilityGrid}>
              <div><h3>Course coordinator</h3>{coordinatorAssignments.length ? <div className={styles.assignmentList}>{coordinatorAssignments.map((assignment) => <div key={assignment.id} className={styles.assignmentItem}><span><strong>{assignment.course_title}</strong><small>Coordinator responsibility</small></span><button type="button" disabled={working} onClick={() => perform(() => adminRemoveCourseCoordinator(assignment.id), "Course coordinator assignment removed.")}>Remove</button></div>)}</div> : <div className={styles.emptyState}>No coordinator courses assigned.</div>}<form className={styles.assignmentForm} onSubmit={(event) => { event.preventDefault(); perform(() => adminAssignCourseCoordinator({ faculty_id: Number(id), course_id: Number(courseId) }), "Course coordinator assigned.").then(() => setCourseId("")); }}><label htmlFor="profile-course">Assign course coordinator</label><div><select id="profile-course" value={courseId} onChange={(event) => setCourseId(event.target.value)} required><option value="">Select course...</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select><button type="submit" disabled={working}>Assign</button></div></form></div>
              <div><h3>Subject expert</h3>{expertAssignments.length ? <div className={styles.assignmentList}>{expertAssignments.map((assignment) => <div key={assignment.id} className={styles.assignmentItem}><span><strong>{assignment.subject_name}</strong><small>Subject-expert responsibility</small></span><button type="button" disabled={working} onClick={() => perform(() => adminRemoveSubjectExpert(assignment.id), "Subject-expert assignment removed.")}>Remove</button></div>)}</div> : <div className={styles.emptyState}>No expert subjects assigned.</div>}<form className={styles.assignmentForm} onSubmit={(event) => { event.preventDefault(); perform(() => adminAssignSubjectExpert({ faculty_id: Number(id), subject_id: Number(subjectId) }), "Subject expert assigned.").then(() => setSubjectId("")); }}><label htmlFor="profile-subject">Assign subject expert</label><div><select id="profile-subject" value={subjectId} onChange={(event) => setSubjectId(event.target.value)} required><option value="">Select subject...</option>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select><button type="submit" disabled={working}>Assign</button></div></form><form className={styles.assignmentForm} onSubmit={(event) => { event.preventDefault(); perform(async () => { const response = await adminCreateSubject({ name: newSubjectName.trim() }); setSubjectId(String(response.data.id)); setNewSubjectName(""); }, "Subject created."); }}><label htmlFor="profile-new-subject">Create a new subject</label><div><input id="profile-new-subject" value={newSubjectName} onChange={(event) => setNewSubjectName(event.target.value)} placeholder="Subject name" required /><button type="submit" disabled={working}>Create</button></div></form></div>
            </div></DetailCard>}

            {kind === "student" ? <StudentActivitySections profile={profile} record={record} /> : <FacultyActivitySections profile={profile} />}

            <DetailCard icon={ShieldCheckIcon} title="Account and verification" description="Registration readiness and verified institutional contact."><Details fields={[{ label: "Registration status", value: profileStatusLabel(record.registration_status), tone: pending ? "warning" : "success" }, { label: "Account status", value: record.is_active ? "Enabled" : "Inactive", tone: record.is_active ? "success" : "warning" }, { label: "Email verification", value: record.email_verified ? "Verified" : "Not verified", tone: record.email_verified ? "success" : "warning" }, { label: "Mobile verification", value: record.mobile_verified ? "Verified" : "Not verified", tone: record.mobile_verified ? "success" : "warning" }]} /><button type="button" className={styles.accountButton} disabled={working} onClick={() => perform(() => record.is_active ? config.deactivate(record.id) : config.activate(record.id), record.is_active ? `${config.label} account deactivated.` : `${config.label} account activated.`)}>{record.is_active ? "Deactivate account" : "Activate account"}</button></DetailCard>
            <DetailCard icon={ClockIcon} title="Record activity" description="Institutional record history displayed in Indian Standard Time."><Details fields={[{ label: "Created", value: profileDateLabel(record.created_at) }, { label: "Last updated", value: profileDateLabel(record.updated_at) }, { label: "Last login", value: record.last_login_available ? profileDateLabel(record.last_login_at) : "No login recorded", wide: true }]} /><p className={styles.securityNote}><CheckBadgeIcon aria-hidden="true" /> Profile access is restricted to authorized SYS administrators.</p></DetailCard>
          </div>
        </>}
      </main>
    </AdminShell>
  </>;
}
