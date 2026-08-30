import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import {
  AcademicCapIcon,
  ArrowRightIcon,
  BookOpenIcon,
  ChartBarIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import { getApiErrorMessage, getRoleDashboard } from "../../src/api";
import {
  clearSession,
  getToken,
  roleDisplayLabel,
  roleLandingPath,
} from "../../src/auth";
import styles from "./RoleDashboard.module.css";
import WorkspaceBreadcrumbs from "./WorkspaceBreadcrumbs";

const METRIC_ICONS = [
  AcademicCapIcon,
  BookOpenIcon,
  UserGroupIcon,
  ChartBarIcon,
];

function CourseList({ courses, student }) {
  if (!courses?.length) {
    return (
      <div className={styles.empty}>
        {student
          ? "You are not enrolled in a SYS course yet. Explore published courses to begin."
          : "No course-coordinator assignment is available yet."}
      </div>
    );
  }

  return courses.map((course) => (
    <div className={styles.item} key={course.id}>
      <div>
        <strong>{course.title}</strong>
        <small>
          {course.programme_code || "SYS course"}
          {course.responsibility
            ? ` · ${course.responsibility.replaceAll("_", " ")}`
            : ""}
        </small>
      </div>
      <Link href={`/courses/${course.id}/workspace`}>
        Open <ArrowRightIcon aria-hidden="true" />
      </Link>
    </div>
  ));
}

function SubjectList({ subjects }) {
  if (!subjects?.length) {
    return (
      <div className={styles.empty}>
        No subject-expert assignment is available yet.
      </div>
    );
  }

  return subjects.map((subject) => (
    <div className={styles.item} key={subject.id}>
      <div>
        <strong>{subject.name}</strong>
        <small>{subject.course_title || "Assigned course"} · Subject expert</small>
      </div>
      <Link href={subject.review_id && subject.review_task_id
        ? `/courses/${subject.course_id}/syllabus/reviews?mode=expert&review=${subject.review_id}&subject=${subject.review_task_id}`
        : `/courses/${subject.course_id}/workspace`}>
        {subject.review_status === "IN_REVIEW" ? "Review" : "Open"} <ArrowRightIcon aria-hidden="true" />
      </Link>
    </div>
  ));
}

export default function RoleDashboard({ expectedRole }) {
  const router = useRouter();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    if (!getToken()) {
      router.replace("/login?reason=unauthorized");
      return undefined;
    }

    getRoleDashboard()
      .then(({ data: payload }) => {
        if (!active) return;

        if (payload?.role !== expectedRole) {
          const destination = roleLandingPath(payload?.role);
          if (destination) {
            router.replace(destination);
          } else {
            clearSession();
            router.replace("/login?reason=unauthorized");
          }
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
            "Your SYS dashboard could not be loaded.",
          ),
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [expectedRole, router]);

  const student = expectedRole === "student";
  const summary = Object.entries(data?.summary || {});

  return (
    <>
      <Head>
        <title>{roleDisplayLabel(expectedRole)} Dashboard | SYS</title>
      </Head>

      <main className={`${styles.page} role-page`}>
        <WorkspaceBreadcrumbs items={[{label:student?"Student Workspace":"Faculty Workspace"}]} />
        <section className={styles.hero}>
          <div className={styles.heroIdentity}>
            {data?.identity?.photo_url ? (
              <img className={styles.heroPhoto} src={data.identity.photo_url} alt={`${data.identity.name} profile`} />
            ) : null}
            <div>
            <p className={styles.eyebrow}>
              {student
                ? "STUDENT LEARNING WORKSPACE"
                : "FACULTY ACADEMIC WORKSPACE"}
            </p>
            <h1>
              Welcome, {data?.identity?.name || roleDisplayLabel(expectedRole)}
            </h1>
            <p>
              {student
                ? "Continue building the knowledge and skills needed for your successful future."
                : "Review your assigned courses, subjects, students, and academic actions."}
            </p>
            </div>
          </div>
          <div className={styles.heroActions}>
            <span className={styles.role}>{roleDisplayLabel(expectedRole)}</span>
            <Link href="/account/profile" className={styles.profileAction}>View and edit profile</Link>
          </div>
        </section>

        {error ? (
          <div className={styles.error} role="alert">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className={styles.loading}>
            Preparing your authorized SYS workspace…
          </div>
        ) : data ? (
          <>
            <section className={styles.metrics}>
              {summary.map(([key, value], index) => {
                const Icon = METRIC_ICONS[index % METRIC_ICONS.length];
                return (
                  <article key={key}>
                    <Icon aria-hidden="true" />
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>
                      {value === "NOT_STARTED" ? "Not started" : value}
                    </strong>
                  </article>
                );
              })}
            </section>

            <section className={styles.grid}>
              <article className={styles.card} id="assigned-courses">
                <h2>{student ? "My enrolled courses" : "My assigned courses"}</h2>
                <p>
                  {student
                    ? "Published SYS courses connected to your student account."
                    : "Courses where you hold course-coordinator responsibility."}
                </p>
                <CourseList courses={data.courses} student={student} />
                {student ? (
                  <Link href="/courses" className={styles.explore}>
                    Explore published courses <ArrowRightIcon aria-hidden="true" />
                  </Link>
                ) : null}
              </article>

              <article className={styles.card}>
                <h2>{student ? "Continue learning" : "My assigned subjects"}</h2>
                <p>
                  {student
                    ? "Your next learning action will appear after course enrollment and learning begins."
                    : "Subjects where you hold subject-expert responsibility."}
                </p>
                {student ? (
                  <div className={styles.empty}>Learning has not started yet.</div>
                ) : (
                  <SubjectList subjects={data.subjects} />
                )}
              </article>
            </section>
          </>
        ) : null}
      </main>
    </>
  );
}
