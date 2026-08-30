import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import {
  AcademicCapIcon,
  ArrowDownTrayIcon,
  ArrowRightIcon,
  BookOpenIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/react/24/outline";
import {
  downloadMyCoordinatorCoursesPdf,
  downloadMySubjectExpertAssignmentsPdf,
  getApiErrorMessage,
  getRoleDashboard,
} from "../../src/api";
import { clearSession, getToken, roleLandingPath } from "../../src/auth";
import { downloadBlob } from "../../src/adminMaster";
import { courseReportFilename } from "../../src/courseReports";
import WorkspaceBreadcrumbs from "./WorkspaceBreadcrumbs";
import styles from "./FacultyAssignedCourses.module.css";

const reviewStatusLabel = (status) => {
  if (status === "RECOMMENDED") return "Review recommended for final approval";
  return (status || "ASSIGNED").replaceAll("_", " ");
};

export default function FacultyResponsibilityCourses({ mode }) {
  const router = useRouter();
  const [data, setData] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [downloadingPortfolio, setDownloadingPortfolio] = useState(false);
  const coordinatorMode = mode === "coordinator";
  useEffect(() => {
    if (!getToken()) {
      router.replace("/login?reason=unauthorized");
      return;
    }
    let active = true;
    getRoleDashboard()
      .then(({ data: payload }) => {
        if (!active) return;
        if (payload?.role !== "faculty") {
          router.replace(
            roleLandingPath(payload?.role) || "/login?reason=unauthorized",
          );
          return;
        }
        setData(payload);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError?.response?.status === 401) {
          clearSession();
          router.replace("/login?reason=expired");
          return;
        }
        setError(
          getApiErrorMessage(
            requestError,
            "Your academic responsibilities could not be loaded.",
          ),
        );
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [router]);
  const groupedSubjects = useMemo(
    () =>
      Object.values(
        (data?.subjects || []).reduce((groups, subject) => {
          groups[subject.course_id] ||= {
            id: subject.course_id,
            title: subject.course_title || "Assigned course",
            subjects: [],
          };
          groups[subject.course_id].subjects.push(subject);
          return groups;
        }, {}),
      ),
    [data],
  );
  const title = coordinatorMode
    ? "Coordinator courses"
    : "Subject expert courses";
  const downloadCoordinatorPortfolio = async () => {
    if (downloadingPortfolio) return;
    setDownloadingPortfolio(true);
    setError("");
    try {
      const response = await downloadMyCoordinatorCoursesPdf();
      downloadBlob(
        response.data,
        courseReportFilename(response, {
          scope: "Course",
          type: "Profile",
          identifier: "Coordinator_Assigned_Courses",
        }),
      );
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "Unable to download your assigned-courses PDF.",
        ),
      );
    } finally {
      setDownloadingPortfolio(false);
    }
  };
  const downloadSubjectPortfolio = async () => {
    if (downloadingPortfolio) return;
    setDownloadingPortfolio(true);
    setError("");
    try {
      const response = await downloadMySubjectExpertAssignmentsPdf();
      downloadBlob(
        response.data,
        courseReportFilename(response, {
          scope: "Subject",
          type: "Profile",
          identifier: "Subject_Expert_Assignments",
        }),
      );
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "Unable to download your assigned-subjects PDF.",
        ),
      );
    } finally {
      setDownloadingPortfolio(false);
    }
  };
  return (
    <main className={styles.page}>
      <Head>
        <title>{title} | SYS</title>
      </Head>
      <WorkspaceBreadcrumbs
        items={[
          { label: "Faculty Workspace", href: "/faculty-dashboard" },
          { label: "Assigned Courses" },
          { label: title },
        ]}
      />
      <header className={styles.heading}>
        <div>
          <span>FACULTY WORKSPACE · ACADEMIC RESPONSIBILITIES</span>
          <h1>{title}</h1>
          <p>
            {coordinatorMode
              ? "Govern complete courses assigned to you as course coordinator."
              : "Review and recommend syllabus subjects assigned to you across SYS courses."}
          </p>
        </div>
        {coordinatorMode && data?.courses?.length > 0 && (
          <button
            type="button"
            className={styles.portfolioDownload}
            onClick={downloadCoordinatorPortfolio}
            disabled={downloadingPortfolio}
          >
            <ArrowDownTrayIcon />
            {downloadingPortfolio
              ? "Preparing assigned courses PDF…"
              : "Download assigned courses PDF"}
          </button>
        )}
        {!coordinatorMode && groupedSubjects.length > 0 && (
          <button
            type="button"
            className={styles.portfolioDownload}
            onClick={downloadSubjectPortfolio}
            disabled={downloadingPortfolio}
          >
            <ArrowDownTrayIcon />
            {downloadingPortfolio
              ? "Preparing assigned subjects PDF…"
              : "Download assigned subjects PDF"}
          </button>
        )}
      </header>
      {loading && (
        <div className={styles.state}>Loading your academic assignments…</div>
      )}
      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}
      {!loading && data && (
        <section className={styles.grid}>
          {coordinatorMode
            ? (data.courses || []).map((course) => (
                <article className={styles.course} key={course.id}>
                  <div className={styles.courseTitle}>
                    <AcademicCapIcon />
                    <div>
                      <small>COURSE COORDINATOR</small>
                      <h2>{course.title}</h2>
                      <p>{course.programme_code || "SYS course"}</p>
                    </div>
                  </div>
                  <div className={styles.responsibilityActions}>
                    <Link href={`/courses/${course.id}/workspace`}>
                      <BookOpenIcon />
                      Course workspace
                    </Link>
                    <Link href={`/courses/${course.id}/syllabus`}>
                      <ClipboardDocumentCheckIcon />
                      Syllabus structure
                    </Link>
                    <Link href={`/courses/${course.id}/syllabus/reviews`}>
                      <ClipboardDocumentCheckIcon />
                      Reviews & approvals
                    </Link>
                  </div>
                </article>
              ))
            : groupedSubjects.map((course) => (
                <article className={styles.course} key={course.id}>
                  <div className={styles.courseTitle}>
                    <BookOpenIcon />
                    <div>
                      <small>SUBJECT EXPERT COURSE</small>
                      <h2>{course.title}</h2>
                      <p>
                        {course.subjects.length} assigned subject
                        {course.subjects.length === 1 ? "" : "s"}
                      </p>
                    </div>
                  </div>
                  <div className={styles.subjectList}>
                    <div className={styles.subjectListHeader}>
                      <span>Subject</span>
                      <span>Review status</span>
                      <span>Action</span>
                    </div>
                    {course.subjects.map((subject) => (
                      <article key={subject.id}>
                        <Link
                          className={styles.subjectNameLink}
                          href={{
                            pathname: `/faculty/subject-expert-courses/${course.id}/subject`,
                            query: subject.review_task_id
                              ? { reviewTaskId: subject.review_task_id }
                              : { subjectId: subject.id },
                          }}
                        >
                          {subject.name}
                        </Link>
                        <span
                          className={`${styles.reviewStatus} ${
                            subject.review_status === "RECOMMENDED"
                              ? styles.recommended
                              : ""
                          }`}
                        >
                          {reviewStatusLabel(subject.review_status)}
                        </span>
                        <div className={styles.subjectActions}>
                          <Link
                            href={{
                              pathname: `/faculty/subject-expert-courses/${course.id}/subject`,
                              query: subject.review_task_id
                                ? { reviewTaskId: subject.review_task_id }
                                : { subjectId: subject.id },
                            }}
                          >
                            View subject
                          </Link>
                          <Link
                            href={
                              subject.review_id && subject.review_task_id
                                ? `/courses/${course.id}/syllabus/reviews?mode=expert&review=${subject.review_id}&subject=${subject.review_task_id}`
                                : `/courses/${course.id}/workspace`
                            }
                          >
                            {subject.review_status === "RECOMMENDED"
                              ? "View review"
                              : "Open review"}{" "}
                            <ArrowRightIcon />
                          </Link>
                        </div>
                      </article>
                    ))}
                  </div>
                </article>
              ))}
          {((coordinatorMode ? data.courses : groupedSubjects) || []).length ===
            0 && (
            <div className={styles.state}>
              No {coordinatorMode ? "course-coordinator" : "subject-expert"}{" "}
              responsibility is assigned to this account.
            </div>
          )}
        </section>
      )}
    </main>
  );
}
