import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  AcademicCapIcon,
  ArrowDownTrayIcon,
  BookOpenIcon,
  ChartBarIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/react/24/outline";
import {
  downloadCourseProfilePdf,
  getApiErrorMessage,
  getCourseWorkspace,
  launchCourseTopicLearning,
} from "../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../src/auth";
import { downloadBlob } from "../../../src/adminMaster";
import { courseReportFilename } from "../../../src/courseReports";
import styles from "../../../components/auth/CourseLearningWorkspace.module.css";
import ApprovedSyllabusDownload from "../../../components/syllabus/ApprovedSyllabusDownload";
import { courseListLink, syllabusLink } from "../../../src/workspaceNavigation";
import WorkspaceBreadcrumbs from "../../../components/auth/WorkspaceBreadcrumbs";

const EMPTY_SECTIONS = [
  ["assessments", "Assessments", ClipboardDocumentCheckIcon],
  ["remedial", "Remedial learning", AcademicCapIcon],
  ["mastery", "Mastery practice", ChartBarIcon],
  ["materials", "Course materials", BookOpenIcon],
];

function Weight({ value, scope }) {
  return (
    <span className={styles.note}>
      {value == null
        ? "Weightage not configured"
        : `Configured weightage: ${value}% within ${scope}`}
    </span>
  );
}

function Syllabus({
  subjects,
  learning,
  role,
  busyTopic,
  onLaunch,
  focusTopic,
  draft,
}) {
  if (!subjects?.length) {
    return (
      <p className={styles.empty}>
        The course syllabus has not been published yet.
      </p>
    );
  }

  return subjects.map((subject) => (
    <details className={styles.subject} key={subject.id} open>
      <summary>
        <span>{subject.name}</span>
        <span>{subject.units.length} units</span>
      </summary>
      <Weight value={subject.weight_percent} scope="course" />
      {!draft && (
        <ApprovedSyllabusDownload
          courseId={learning?.course_id}
          subjectId={subject.id}
          label="Download approved subject syllabus"
        />
      )}
      {role === "student" && (
        <p className={styles.note}>
          {
            subject.units
              .flatMap((u) => u.topics)
              .filter((t) => learning?.topic_states?.[t.id] === "COMPLETED")
              .length
          }{" "}
          / {subject.units.flatMap((u) => u.topics).length} topics completed
        </p>
      )}
      {subject.experts.length ? (
        <p className={styles.experts}>
          Subject experts:{" "}
          {subject.experts.map((expert) => expert.name).join(", ")}
        </p>
      ) : (
        <p className={styles.experts}>
          No subject expert has been assigned yet.
        </p>
      )}
      {subject.units.length ? (
        subject.units.map((unit) => (
          <details
            className={styles.unit}
            key={unit.id}
            open={
              unit.topics.some((t) => String(t.id) === String(focusTopic)) ||
              undefined
            }
          >
            <summary>
              {unit.sequence}. {unit.name}
            </summary>
            <Weight value={unit.weight_percent} scope="subject" />
            {role === "student" && (
              <p className={styles.note}>
                {
                  unit.topics.filter(
                    (t) => learning?.topic_states?.[t.id] === "COMPLETED",
                  ).length
                }{" "}
                / {unit.topics.length} topics completed
              </p>
            )}
            {unit.topics.length ? (
              <ul className={styles.topics}>
                {unit.topics.map((topic) => (
                  <li
                    className={styles.topic}
                    key={topic.id}
                    id={`topic-${topic.id}`}
                  >
                    <div className={styles.topicHeading}>
                      <div>
                        <strong>{topic.name}</strong>
                        {role === "student" && (
                          <span className={styles.lessonState}>
                            {(
                              learning?.topic_states?.[topic.id] ||
                              "NOT_STARTED"
                            ).replaceAll("_", " ")}
                          </span>
                        )}
                        <p className={styles.note}>
                          {topic.description ||
                            "No topic overview has been added."}
                        </p>
                        <Weight value={topic.weight_percent} scope="unit" />
                      </div>
                      {role === "student" ? (
                        <button
                          type="button"
                          className={styles.learnButton}
                          disabled={busyTopic !== null}
                          onClick={() => onLaunch(topic)}
                        >
                          {busyTopic === topic.id
                            ? "Preparing classroom…"
                            : learning?.topic_sessions?.[topic.id]?.can_resume
                              ? "Resume AI lesson"
                              : "Start AI lesson"}
                        </button>
                      ) : !draft ? (
                        <Link
                          className={styles.manageLink}
                          href={`/learning-sessions?course_id=${learning?.course_id || ""}&subject_id=${subject.id}&topic_id=${topic.id}`}
                        >
                          Manage sessions
                        </Link>
                      ) : (
                        <span className={styles.draftLabel}>
                          Available after final approval
                        </span>
                      )}
                    </div>
                    {topic.subtopics.length ? (
                      <ul>
                        {topic.subtopics.map((subtopic) => (
                          <li key={subtopic.id}>
                            <details>
                              <summary>{subtopic.name}</summary>
                              <p>
                                {subtopic.description ||
                                  "No subtopic overview has been added."}
                              </p>
                              <Weight
                                value={subtopic.weight_percent}
                                scope="topic"
                              />
                              {role === "student" && (
                                <>
                                  <p className={styles.note}>
                                    Subtopic learning:{" "}
                                    {(
                                      learning?.subtopic_states?.[
                                        subtopic.id
                                      ] || "NOT_STARTED"
                                    ).replaceAll("_", " ")}
                                  </p>
                                  <button
                                    className={styles.learnButton}
                                    disabled={busyTopic !== null}
                                    onClick={() => onLaunch(topic, subtopic.id)}
                                  >
                                    Open subtopic lesson
                                  </button>
                                </>
                              )}
                            </details>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className={styles.note}>
                        No subtopics added yet.
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.empty}>No topics added yet.</p>
            )}
          </details>
        ))
      ) : (
        <p className={styles.empty}>No syllabus units added yet.</p>
      )}
    </details>
  ));
}

export default function CourseLearningWorkspace() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyTopic, setBusyTopic] = useState(null);
  const [downloadingProfile, setDownloadingProfile] = useState(false);

  useEffect(() => {
    if (!router.isReady || !id) return;
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    let active = true;
    setData(null);
    setLoading(true);
    setError("");
    getCourseWorkspace(id)
      .then(({ data: payload }) => {
        if (active) setData(payload);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(
          getApiErrorMessage(
            requestError,
            "Your course workspace could not be opened.",
          ),
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id, router.isReady]);

  const launchTopic = async (topic, subtopicId = null) => {
    setBusyTopic(topic.id);
    setError("");
    try {
      const { data: launch } = await launchCourseTopicLearning(
        id,
        topic.id,
        subtopicId,
      );
      await router.push(launch.classroom_path);
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "The AI Lecturer classroom could not be prepared.",
        ),
      );
      setBusyTopic(null);
    }
  };

  const course = data?.course;
  const back = courseListLink(data?.role);
  const downloadCourseInformation = async () => {
    if (!course || downloadingProfile) return;
    setDownloadingProfile(true);
    setError("");
    try {
      const response = await downloadCourseProfilePdf(course.id);
      downloadBlob(
        response.data,
        courseReportFilename(response, {
          scope: "Course",
          type: "Profile",
          identifier: course.programme_code || course.title,
        }),
      );
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "Unable to download the course information PDF.",
        ),
      );
    } finally {
      setDownloadingProfile(false);
    }
  };
  return (
    <main className={styles.page}>
      <Head>
        <title>{course?.title || "Course"} Learning Workspace | SYS</title>
      </Head>
      {data && data.role === "faculty" ? (
        <WorkspaceBreadcrumbs
          items={[
            { label: "Faculty Workspace", href: "/faculty-dashboard" },
            { label: "Assigned Courses" },
            {
              label: "Coordinator Courses",
              href: "/faculty/coordinator-courses",
            },
            { label: course?.title || "Course Workspace" },
          ]}
        />
      ) : (
        data && (
          <Link className={styles.back} href={back.href}>
            ← {back.label}
          </Link>
        )
      )}
      {loading ? (
        <p className={styles.empty}>
          Opening your authorized SYS learning workspace…
        </p>
      ) : null}
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      {course ? (
        <>
          <section className={styles.hero}>
            <p className={styles.eyebrow}>SYS COURSE LEARNING WORKSPACE</p>
            <h1>{course.title}</h1>
            <p>
              {course.description ||
                course.target_purpose ||
                "A structured SYS learning and examination-preparation course."}
            </p>
            <div className={styles.badges}>
              <span>{course.programme_code || "SYS COURSE"}</span>
              <span>{course.subject_count} subjects</span>
              <span>{course.unit_count} units</span>
              <span>{course.student_count} enrolled students</span>
            </div>
            {data.syllabus_status?.is_draft && (
              <p className={styles.draftNotice}>
                Coordinator preview · Configured syllabus under review · Not
                visible to students
              </p>
            )}
            <p className={styles.coordinators}>
              Course coordinator:{" "}
              {course.course_coordinators?.length
                ? course.course_coordinators
                    .map((item) => item.faculty_name)
                    .join(", ")
                : "Not assigned yet"}
            </p>
            {data.role === "faculty" && (
              <button
                type="button"
                className={styles.courseDownload}
                onClick={downloadCourseInformation}
                disabled={downloadingProfile}
              >
                <ArrowDownTrayIcon aria-hidden="true" />
                {downloadingProfile
                  ? "Preparing course information…"
                  : "Download course information PDF"}
              </button>
            )}
          </section>
          {data.role === "student" && (
            <section className={styles.card}>
              <h2>Your learning progress</h2>
              <p>
                {data.learning?.completed_topics || 0} of{" "}
                {data.learning?.total_topics || 0} topics completed ·{" "}
                {data.learning?.progress_percent || 0}%
              </p>
              <progress
                style={{ width: "100%" }}
                value={data.learning?.completed_topics || 0}
                max={data.learning?.total_topics || 1}
                aria-label="Completed syllabus topics"
              />
              <p className={styles.note}>
                Completion is based on your learning records, not assessment
                mastery. Subtopics show their own separately recorded progress.
              </p>
              {data.learning?.continue_learning && (
                <Link
                  className={styles.learnButton}
                  href={data.learning.continue_learning.classroom_path}
                >
                  Continue learning
                </Link>
              )}
            </section>
          )}
          <section className={styles.layout}>
            <article className={styles.card}>
              <h2>Structured course syllabus</h2>
              <p className={styles.description}>
                Subject → Unit → Topic → Subtopic
              </p>
              <div className={styles.syllabusActions}>
                {!data.syllabus_status?.is_draft && (
                  <ApprovedSyllabusDownload courseId={course.id} />
                )}
                {data.role !== "student" && (
                  <Link
                    className={styles.manageLink}
                    href={syllabusLink(data.role, course.id)}
                  >
                    Manage syllabus / coordinator approvals
                  </Link>
                )}
              </div>
              <Syllabus
                subjects={data.syllabus}
                learning={{ ...data.learning, course_id: course.id }}
                role={data.role}
                busyTopic={busyTopic}
                onLaunch={launchTopic}
                focusTopic={router.query.topic_id}
                draft={data.syllabus_status?.is_draft}
              />
            </article>
            <section className={styles.progress}>
              <article className={`${styles.card} ${styles.learningCard}`}>
                <h2>
                  <BookOpenIcon aria-hidden="true" /> AI learning sessions
                </h2>
                <div className={styles.learningStats}>
                  <span>
                    <strong>{data.learning?.active_count || 0}</strong> active
                  </span>
                  <span>
                    <strong>{data.learning?.completed_count || 0}</strong>{" "}
                    completed
                  </span>
                </div>
                <p className={styles.description}>{data.learning?.message}</p>
              </article>
              {EMPTY_SECTIONS.map(([key, title, Icon]) => (
                <article className={styles.card} key={key}>
                  <h2>
                    <Icon aria-hidden="true" /> {title}
                  </h2>
                  <p className={styles.description}>
                    {data[key]?.message || "No information is available yet."}
                  </p>
                </article>
              ))}
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
