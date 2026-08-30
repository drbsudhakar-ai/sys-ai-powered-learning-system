import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { ArrowDownTrayIcon, ArrowLeftIcon } from "@heroicons/react/24/outline";
import { downloadCourseProfilePdf, downloadCourseSyllabusPdf, downloadSubjectProfilePdf, downloadSubjectSyllabusPdf, getApiErrorMessage, getCourseAcademicWeightages, getMe } from "../../../src/api";
import { downloadBlob } from "../../../src/adminMaster";
import { courseReportFilename } from "../../../src/courseReports";
import styles from "../../../components/admin/CourseMasterWorkspace.module.css";

export default function AcademicCourseReportsPage() {
  const router = useRouter();
  const courseId = router.query.id;
  const [user, setUser] = useState(null);
  const [ownership, setOwnership] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!router.isReady || !courseId) return undefined;
    let active = true;
    setLoading(true); setError("");
    Promise.all([getMe(), getCourseAcademicWeightages(courseId)]).then(([userResponse, scopeResponse]) => { if (active) { setUser(userResponse.data); setOwnership(scopeResponse.data); } }).catch((requestError) => { if (active) setError(getApiErrorMessage(requestError, "You do not have an academic responsibility for this course.")); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId, router.isReady]);

  async function download(type, subject = null) {
    if (!ownership || downloading) return;
    setDownloading(`${type}-${subject?.id || "course"}`); setError("");
    try {
      const response = subject ? await (type === "syllabus" ? downloadSubjectSyllabusPdf(courseId, subject.id) : downloadSubjectProfilePdf(courseId, subject.id)) : await (type === "syllabus" ? downloadCourseSyllabusPdf(courseId) : downloadCourseProfilePdf(courseId));
      downloadBlob(response.data, courseReportFilename(response, { scope: subject ? "Subject" : "Course", type: type === "syllabus" ? "Syllabus" : "Profile", identifier: subject?.name || ownership.course_title }));
    } catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to download this authorized academic report.")); }
    finally { setDownloading(""); }
  }

  const subjects = (ownership?.subjects || []).filter((subject) => ownership?.can_manage_course || subject.editable);

  return <><Head><title>{ownership?.course_title || "Academic"} Reports | SYS</title><meta name="description" content="Download authorized SYS course and subject institutional profile reports." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head><main className={styles.workspace}><Link href="/courses" className={styles.back}><ArrowLeftIcon />Back to courses</Link>{error && <div className={styles.error} role="alert">{error}</div>}{loading ? <div className={styles.loading}>Verifying academic responsibility and preparing authorized reports…</div> : !ownership ? <div className={styles.empty}><h3>Academic reports unavailable</h3><p>Only assigned course coordinators, subject experts, and SYS administrators may access these reports.</p></div> : <><section className={styles.hero}><div><span className={styles.eyebrow}>SYS academic reports · authorized ownership</span><h1>{ownership.course_title}</h1><p>{ownership.can_manage_course ? "Complete course-level academic reporting" : "Reports limited to your assigned academic subjects"}</p><div className={styles.heroMeta}><span className={styles.heroTag}>{user?.name || "Authorized academic faculty"}</span><span className={styles.heroTag}>{ownership.can_manage_course ? "Course coordinator or administrator" : "Assigned subject expert"}</span></div></div>{ownership.can_manage_course && <div className={styles.heroActions}><button type="button" className={styles.button} disabled={Boolean(downloading)} onClick={() => download("profile")}><ArrowDownTrayIcon />Download course profile PDF</button><button type="button" className={styles.buttonLight} disabled={Boolean(downloading)} onClick={() => download("syllabus")}><ArrowDownTrayIcon />Download approved syllabus PDF</button></div>}</section><section className={styles.detailCard}><h2>Authorized subject reports</h2><p>Subject documents contain only the selected subject, its syllabus, assigned experts, and subject-scoped academic activity.</p>{subjects.length ? <div className={styles.list}>{subjects.map((subject) => <article className={styles.person} key={subject.id}><strong>{subject.name}</strong><small>{subject.weight_percent === null || subject.weight_percent === undefined ? "Subject weightage not configured" : `${subject.weight_percent}% course weightage`} · {subject.units?.length || 0} units</small><div className={styles.actions} style={{ marginTop: 10 }}><button type="button" className={styles.button} disabled={Boolean(downloading)} onClick={() => download("profile", subject)}><ArrowDownTrayIcon />Download subject profile PDF</button><button type="button" className={styles.button} disabled={Boolean(downloading)} onClick={() => download("syllabus", subject)}><ArrowDownTrayIcon />Download subject syllabus PDF</button></div></article>)}</div> : <div className={styles.notice}>No assigned syllabus subjects are available for reporting.</div>}</section></>}</main></>;
}
