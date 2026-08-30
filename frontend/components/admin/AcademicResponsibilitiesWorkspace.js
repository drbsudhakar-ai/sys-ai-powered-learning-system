import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowPathIcon, MagnifyingGlassIcon, PlusIcon, TrashIcon, UserGroupIcon } from "@heroicons/react/24/outline";
import API, { adminAssignCourseCoordinator, adminAssignSubjectExpert, adminListCourseCoordinators, adminListFaculty, adminListSubjectExperts, adminListSubjects, adminRemoveCourseCoordinator, adminRemoveSubjectExpert, getAdminOperationsSummary, getApiErrorMessage, getCourses } from "../../src/api";
import { availableFaculty, filterResponsibilities, ownershipSummary, responsibilityRows } from "../../src/academicOwnership";
import AdminShell from "./AdminShell";
import { configuredOwnership } from "../../src/syllabusConfiguration";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./AcademicResponsibilitiesWorkspace.module.css";

function Metric({ label, value, detail }) {
  return <article className={styles.metric}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

export default function AcademicResponsibilitiesWorkspace() {
  const router = useRouter();
  const access = useAdminAccess();
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [coordinators, setCoordinators] = useState([]);
  const [experts, setExperts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [courseFilter, setCourseFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [assignmentType, setAssignmentType] = useState("course_coordinator");
  const [courseId, setCourseId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [facultyId, setFacultyId] = useState("");

  const refresh = useCallback(async () => {
    const [courseResponse, subjectResponse, facultyResponse, coordinatorResponse, expertResponse] = await Promise.all([getCourses(), adminListSubjects(), adminListFaculty(), adminListCourseCoordinators(), adminListSubjectExperts()]);
    for (const response of [courseResponse, subjectResponse, facultyResponse, coordinatorResponse, expertResponse]) if (!Array.isArray(response.data)) throw new Error("SYS returned an invalid academic ownership response.");
    const configured = configuredOwnership(courseResponse.data, subjectResponse.data, expertResponse.data);
    setCourses(courseResponse.data); setSubjects(configured.subjects); setFaculty(facultyResponse.data); setCoordinators(coordinatorResponse.data); setExperts(configured.experts);
  }, []);

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    let current = true;
    setLoading(true); setError("");
    refresh().catch((requestError) => { if (current) setError(getApiErrorMessage(requestError, "Unable to load academic responsibilities.")); }).finally(() => { if (current) setLoading(false); });
    getAdminOperationsSummary().then(({ data }) => { if (current) setSummary(data || null); }).catch(() => {});
    return () => { current = false; };
  }, [access.status, refresh]);

  useEffect(() => {
    if (!router.isReady || !router.query.course_id) return;
    const selected = String(router.query.course_id);
    setCourseFilter(selected); setCourseId(selected);
  }, [router.isReady, router.query.course_id]);

  const rows = useMemo(() => responsibilityRows(coordinators, experts, faculty, subjects), [coordinators, experts, faculty, subjects]);
  const filtered = useMemo(() => filterResponsibilities(rows, { search, course: courseFilter, type: typeFilter, department: departmentFilter }), [rows, search, courseFilter, typeFilter, departmentFilter]);
  const counts = useMemo(() => ownershipSummary(courses, subjects, coordinators, experts), [courses, subjects, coordinators, experts]);
  const eligibleFaculty = useMemo(() => availableFaculty(faculty), [faculty]);
  const departments = useMemo(() => [...new Set(faculty.map((person) => person.department).filter(Boolean))].sort(), [faculty]);
  const courseSubjects = useMemo(() => subjects.filter((subject) => String(subject.course_id) === String(courseId)), [subjects, courseId]);

  async function submit(event) {
    event.preventDefault(); setWorking(true); setNotice(""); setError("");
    try {
      if (assignmentType === "course_coordinator") await adminAssignCourseCoordinator({ faculty_id: Number(facultyId), course_id: Number(courseId) });
      else {
        const subject = subjects.find(s => String(s.id) === String(subjectId));
        if (subject?.draft_review_id) await API.post(`/courses/${subject.course_id}/syllabus-review/reviews/${subject.draft_review_id}/subject-action`, { action: "assign", subject_key: subject.subject_key, reviewer_id: Number(facultyId), version: subject.draft_version });
        else await adminAssignSubjectExpert({ faculty_id: Number(facultyId), subject_id: Number(subjectId) });
      }
      await refresh(); setNotice(assignmentType === "course_coordinator" ? "Course coordinator assigned successfully." : "Subject expert assigned successfully."); setFacultyId(""); setSubjectId("");
    } catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to assign academic responsibility.")); }
    finally { setWorking(false); }
  }

  async function remove(row) {
    if (!window.confirm(`Remove ${row.faculty_name} as ${row.responsibility.toLowerCase()}?`)) return;
    setWorking(true); setNotice(""); setError("");
    try { if (row.draft_review_id) await API.post(`/courses/${row.course_id}/syllabus-review/reviews/${row.draft_review_id}/subject-action`, { action: "unassign", subject_key: row.subject_key, version: row.draft_version });
      else await (row.type === "course_coordinator" ? adminRemoveCourseCoordinator(row.id) : adminRemoveSubjectExpert(row.id)); await refresh(); setNotice("Academic responsibility removed successfully."); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to remove academic responsibility.")); }
    finally { setWorking(false); }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the SYS academic ownership workspace." />;
  if (access.status === "error") return <BrandedState type="error" title="Academic responsibilities unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  return <>
    <Head><title>Academic Responsibilities | SYS</title><meta name="description" content="Manage SYS course coordinators, subject experts, and academic ownership." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
    <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="Academic Management" pageTitle="Academic Responsibilities" scopeLabel={summary?.scope_label || "Platform-wide"}>
      <main className={styles.workspace}>
        <header className={styles.heading}><div><span className={styles.eyebrow}>Academic management · Faculty ownership</span><h1>Academic Responsibilities</h1><p>Assign course coordinators, subject experts, and accountable academic ownership.</p></div><div className={styles.actions}><button type="button" className={styles.button} disabled={loading || working} onClick={() => { setLoading(true); refresh().catch((requestError) => setError(getApiErrorMessage(requestError, "Unable to refresh responsibilities."))).finally(() => setLoading(false)); }}><ArrowPathIcon />Refresh</button><Link href="/admin/faculty" className={styles.button}><UserGroupIcon />Faculty Master</Link>{courseFilter !== "all" && <Link href={`/courses/${courseFilter}/reports`} className={styles.button}>Faculty course reports</Link>}</div></header>
        <section className={styles.metrics} aria-label="Academic ownership summary"><Metric label="Course coordinators" value={counts.coordinators} detail="Course-level academic ownership" /><Metric label="Subject experts" value={counts.experts} detail="Subject-level academic ownership" /><Metric label="Courses without coordinator" value={counts.coursesWithoutCoordinator} detail="Courses requiring an owner" /><Metric label="Subjects without expert" value={counts.subjectsWithoutExpert} detail="Subjects requiring an expert" /></section>
        {notice && <div role="status" className={styles.notice}>{notice}</div>}{error && <div role="alert" className={styles.error}>{error}</div>}
        <div className={styles.layout}>
          <section className={styles.panel} aria-label="Academic responsibility assignments"><div className={styles.toolbar}><label className={styles.search}><MagnifyingGlassIcon /><input aria-label="Search academic responsibilities" placeholder="Search faculty, course, subject, or department" value={search} onChange={(event) => setSearch(event.target.value)} /></label><select aria-label="Filter by course" className={styles.select} value={courseFilter} onChange={(event) => setCourseFilter(event.target.value)}><option value="all">All courses</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select><select aria-label="Filter by responsibility" className={styles.select} value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="all">All roles</option><option value="course_coordinator">Coordinator</option><option value="subject_expert">Subject expert</option></select><select aria-label="Filter by department" className={styles.select} value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)}><option value="all">All departments</option>{departments.map((department) => <option key={department} value={department}>{department}</option>)}</select></div>{loading ? <div className={styles.loading}>Loading academic ownership records…</div> : filtered.length ? <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Faculty</th><th>Course and subject</th><th>Responsibility</th><th>Action</th></tr></thead><tbody>{filtered.map((row) => <tr key={`${row.type}-${row.id}`}><td><Link href={`/admin/faculty/${row.faculty_id}`}><strong>{row.faculty_name}</strong></Link><small>{row.faculty?.employee_code || row.faculty_email || "Employee code unavailable"}</small><small>{row.faculty?.department || "Department unavailable"}</small></td><td><Link href={`/admin/courses/${row.course_id}`}><strong>{row.course_title}</strong></Link><small>{row.subject_name}</small></td><td><span className={row.type === "course_coordinator" ? styles.badge : styles.expertBadge}>{row.responsibility}</span></td><td><button type="button" className={styles.danger} disabled={working || row.can_remove === false} title={row.can_remove === false ? "A review is in progress; finish or invalidate it before changing ownership." : undefined} onClick={() => remove(row)} aria-label={`Remove ${row.faculty_name} ${row.responsibility}`}><TrashIcon />Remove</button></td></tr>)}</tbody></table></div> : <div className={styles.empty}><h3>{rows.length ? "No responsibilities match these filters" : "No academic responsibilities assigned yet"}</h3><p>{rows.length ? "Adjust the search or filters to see existing assignments." : "Assign a course coordinator or subject expert to establish academic ownership."}</p></div>}<div className={styles.coverage}><h3>Academic ownership readiness</h3><span className={styles.subtle}>{counts.coursesWithoutCoordinator} courses and {counts.subjectsWithoutExpert} subjects still need academic ownership. </span><Link href="/admin/courses">Open Course Master</Link></div></section>
          <form className={styles.formCard} onSubmit={submit}><h2>Assign responsibility</h2><p>Choose the course, academic role, and eligible faculty member.</p><label htmlFor="ownership-role">Academic responsibility</label><select id="ownership-role" value={assignmentType} onChange={(event) => { setAssignmentType(event.target.value); setSubjectId(""); }}><option value="course_coordinator">Course coordinator</option><option value="subject_expert">Subject expert</option></select><label htmlFor="ownership-course">Course</label><select id="ownership-course" value={courseId} onChange={(event) => { setCourseId(event.target.value); setSubjectId(""); }} required><option value="">Select course...</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}{course.programme_code ? ` · ${course.programme_code}` : ""}</option>)}</select>{assignmentType === "subject_expert" && <><label htmlFor="ownership-subject">Subject</label><select id="ownership-subject" value={subjectId} onChange={(event) => setSubjectId(event.target.value)} required disabled={!courseId}><option value="">{courseId ? "Select course subject..." : "Select a course first..."}</option>{courseSubjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}{subject.draft_review_id ? " · Saved syllabus" : ""}</option>)}</select>{courseId && !courseSubjects.length && <p className={styles.help}>This course has no subjects yet. Add subjects in the course syllabus before assigning experts.</p>}</>}<label htmlFor="ownership-faculty">Faculty member</label><select id="ownership-faculty" value={facultyId} onChange={(event) => setFacultyId(event.target.value)} required><option value="">Select eligible faculty...</option>{eligibleFaculty.map((person) => <option key={person.id} value={person.id}>{person.name}{person.employee_code ? ` · ${person.employee_code}` : ""}{person.department ? ` · ${person.department}` : ""}{person.account_status === "PENDING_ACTIVATION" ? " · Registration pending" : ""}</option>)}</select><button type="submit" className={styles.buttonPrimary} disabled={working || !courseId || !facultyId || (assignmentType === "subject_expert" && !subjectId)}><PlusIcon />{working ? "Saving assignment…" : "Assign academic responsibility"}</button><div className={styles.help}>Course coordinators oversee the complete course. Subject experts own their assigned course subject. Inactive faculty members cannot receive assignments. Faculty awaiting registration can be assigned, but must register before receiving review requests.</div></form>
        </div>
      </main>
    </AdminShell>
  </>;
}
