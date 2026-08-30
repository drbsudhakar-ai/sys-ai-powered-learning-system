import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  ArrowDownTrayIcon,
  BookOpenIcon,
  ScaleIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import {
  downloadSubjectExpertInformationPdf,
  getApiErrorMessage,
  getSubjectExpertInformation,
} from "../../src/api";
import { downloadBlob } from "../../src/adminMaster";
import { courseReportFilename } from "../../src/courseReports";
import WorkspaceBreadcrumbs from "./WorkspaceBreadcrumbs";
import styles from "./SubjectExpertInformation.module.css";

const label = (value) => String(value || "Not configured").replaceAll("_", " ");

export default function SubjectExpertInformation() {
  const router = useRouter();
  const { courseId, subjectId, reviewTaskId } = router.query;
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!router.isReady || !courseId || (!subjectId && !reviewTaskId)) return;
    let active = true;
    getSubjectExpertInformation({
      course_id: courseId,
      ...(reviewTaskId
        ? { review_task_id: reviewTaskId }
        : { subject_id: subjectId }),
    })
      .then(({ data: payload }) => active && setData(payload))
      .catch(
        (requestError) =>
          active &&
          setError(
            getApiErrorMessage(
              requestError,
              "Unable to load this assigned subject.",
            ),
          ),
      );
    return () => {
      active = false;
    };
  }, [router.isReady, courseId, subjectId, reviewTaskId]);

  const subject = data?.subject;
  const course = data?.course;
  const activity = data?.activity || {};
  const assignmentParams = {
    course_id: courseId,
    ...(reviewTaskId
      ? { review_task_id: reviewTaskId }
      : { subject_id: subjectId }),
  };
  const downloadInformation = async () => {
    if (downloading) return;
    setDownloading(true);
    setError("");
    try {
      const response =
        await downloadSubjectExpertInformationPdf(assignmentParams);
      downloadBlob(
        response.data,
        courseReportFilename(response, {
          scope: "Subject",
          type: "Profile",
          identifier: subject?.name || "Assigned_Subject",
        }),
      );
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "Unable to download subject information PDF.",
        ),
      );
    } finally {
      setDownloading(false);
    }
  };
  return (
    <main className={styles.page}>
      <Head>
        <title>{subject?.name || "Subject information"} | SYS</title>
      </Head>
      <WorkspaceBreadcrumbs
        items={[
          { label: "Faculty Workspace", href: "/faculty-dashboard" },
          { label: "Assigned Courses" },
          {
            label: "Subject Expert Courses",
            href: "/faculty/subject-expert-courses",
          },
          { label: subject?.name || "Subject information" },
        ]}
      />
      {error && <div className={styles.error}>{error}</div>}
      {!data && !error && (
        <div className={styles.state}>
          Loading assigned subject information…
        </div>
      )}
      {data && (
        <>
          <header className={styles.hero}>
            <div>
              <span>SUBJECT EXPERT RESPONSIBILITY</span>
              <h1>{subject.name}</h1>
              <p>
                {course.title} · {course.programme_code || "SYS course"}
              </p>
              <div className={styles.tags}>
                <span>{label(data.assignment?.review_status)}</span>
                <span>{data.syllabus_status}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={downloadInformation}
              disabled={downloading}
            >
              <ArrowDownTrayIcon />
              {downloading
                ? "Preparing PDF…"
                : "Download subject information PDF"}
            </button>
          </header>
          <section className={styles.metrics}>
            <article>
              <strong>{subject.units?.length || 0}</strong>
              <span>Units</span>
            </article>
            <article>
              <strong>
                {subject.units?.reduce(
                  (n, unit) => n + (unit.topics?.length || 0),
                  0,
                ) || 0}
              </strong>
              <span>Topics</span>
            </article>
            <article>
              <strong>{activity.students || 0}</strong>
              <span>Course students</span>
            </article>
            <article>
              <strong>{activity.assessments || 0}</strong>
              <span>Assessments</span>
            </article>
          </section>
          {reviewTaskId && data.assignment?.review_status === "APPROVED" && (
            <section className={styles.card}>
              <div className={styles.cardTitle}>
                <ScaleIcon />
                <div>
                  <h2>Subject academic weightages</h2>
                  <p>
                    Configure, verify, and recommend the approved subject branch&apos;s
                    pilot weightages for administrator approval.
                  </p>
                </div>
              </div>
              <Link className={styles.back} href={{ pathname: `/faculty/subject-expert-courses/${courseId}/weightages`, query: { reviewTaskId } }}>
                Review and recommend subject weightages
              </Link>
            </section>
          )}
          <section className={styles.card}>
            <div className={styles.cardTitle}>
              <BookOpenIcon />
              <div>
                <h2>Subject syllabus</h2>
                <p>
                  Configured unit, topic and subtopic structure for this
                  responsibility.
                </p>
              </div>
            </div>
            <div className={styles.syllabus}>
              {subject.units?.length ? (
                subject.units.map((unit) => (
                  <details key={unit.id} open>
                    <summary>
                      {unit.sequence}. {unit.name}
                    </summary>
                    <p>
                      {unit.description ||
                        unit.learning_outcome ||
                        "No unit description configured."}
                    </p>
                    {unit.topics?.map((topic) => (
                      <div className={styles.topic} key={topic.id}>
                        <strong>{topic.name}</strong>
                        {topic.description && <p>{topic.description}</p>}
                        <ul>
                          {topic.subtopics?.map((subtopic) => (
                            <li key={subtopic.id}>{subtopic.name}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </details>
                ))
              ) : (
                <p>No units are configured for this subject yet.</p>
              )}
            </div>
          </section>
          <section className={styles.card}>
            <div className={styles.cardTitle}>
              <UserGroupIcon />
              <div>
                <h2>Students enrolled in the course</h2>
                <p>{data.enrollment_scope}</p>
              </div>
            </div>
            <div className={styles.tableWrap}>
              <table>
                <thead>
                  <tr>
                    <th>Roll number</th>
                    <th>Student</th>
                    <th>Academic programme</th>
                    <th>Year</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.enrolled_students?.length ? (
                    data.enrolled_students.map((student) => (
                      <tr key={student.id}>
                        <td>{student.roll_number || "—"}</td>
                        <td>{student.name}</td>
                        <td>{student.academic_program || "Not recorded"}</td>
                        <td>{student.present_year || "—"}</td>
                        <td>{label(student.status)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5">
                        No active students are enrolled in this course.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
          <Link className={styles.back} href="/faculty/subject-expert-courses">
            Back to Subject Expert Courses
          </Link>
        </>
      )}
    </main>
  );
}
