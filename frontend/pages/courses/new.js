import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import CourseForm from "../../components/CourseForm";
import { createCourse, getApiErrorMessage, getMe } from "../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../src/auth";

const emptyForm = {
  title: "",
  description: "",
  syllabus_url: "",
  resources_url: "",
};

export default function NewCoursePage() {
  const router = useRouter();
  const [formData, setFormData] = useState(emptyForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    (async () => {
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setError("You do not have permission to create courses.");
          setReady(true);
          return;
        }
        setReady(true);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err));
        setReady(true);
      }
    })();
  }, []);

  const onChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!formData.title.trim()) {
      setError("Title is required.");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim() || null,
        syllabus_url: formData.syllabus_url.trim() || null,
        resources_url: formData.resources_url.trim() || null,
      };
      const res = await createCourse(payload);
      setSuccess("Course created successfully.");
      router.push(`/courses/${res.data.id}`);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to create course."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <Link href="/courses" className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline">
        ← Back to courses
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Create Course</h1>
      <p className="mb-6 mt-1 text-sm text-[var(--sys-gray)]">Add a new SYS training course.</p>

      {!ready && <p className="sys-card" role="status">Checking permissions…</p>}
      {ready && error && !formData.title && error.includes("permission") ? (
        <p className="sys-card text-red-600" role="alert">{error}</p>
      ) : null}
      {ready && !(error && error.includes("permission")) && (
        <CourseForm
          formData={formData}
          onChange={onChange}
          onSubmit={onSubmit}
          submitLabel={submitting ? "Creating…" : "Create Course"}
          disabled={submitting}
          error={error}
          success={success}
        />
      )}
    </div>
  );
}
