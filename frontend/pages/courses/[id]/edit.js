import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import CourseForm from "../../../components/CourseForm";
import {
  getApiErrorMessage,
  getCourse,
  getMe,
  updateCourse,
} from "../../../src/api";
import { clearSession, getToken, isStaffRole, redirectToLogin } from "../../../src/auth";

export default function EditCoursePage() {
  const router = useRouter();
  const { id } = router.query;
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    syllabus_url: "",
    resources_url: "",
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    if (!router.isReady) return;
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    if (!id) return;

    (async () => {
      setLoading(true);
      setError("");
      try {
        const me = await getMe();
        if (!isStaffRole(me.data.role)) {
          setAllowed(false);
          setError("You do not have permission to edit courses.");
          setLoading(false);
          return;
        }
        setAllowed(true);
        const res = await getCourse(id);
        const c = res.data;
        setFormData({
          title: c.title || "",
          description: c.description || "",
          syllabus_url: c.syllabus_url || "",
          resources_url: c.resources_url || "",
        });
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        setError(getApiErrorMessage(err, "Unable to load course."));
      } finally {
        setLoading(false);
      }
    })();
  }, [router.isReady, id]);

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
      await updateCourse(id, payload);
      setSuccess("Course updated successfully.");
      router.push(`/courses/${id}`);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err, "Unable to update course."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <Link
        href={id ? `/courses/${id}` : "/courses"}
        className="text-sm font-semibold text-[var(--sys-blue)] no-underline hover:underline"
      >
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-[var(--sys-blue)]">Edit Course</h1>

      {loading && (
        <p className="sys-card mt-6" role="status">
          Loading course…
        </p>
      )}

      {!loading && !allowed && error && (
        <p className="sys-card mt-6 text-red-600" role="alert">
          {error}
        </p>
      )}

      {!loading && allowed && (
        <div className="mt-6">
          <CourseForm
            formData={formData}
            onChange={onChange}
            onSubmit={onSubmit}
            submitLabel={submitting ? "Saving…" : "Save Changes"}
            disabled={submitting}
            error={error}
            success={success}
          />
        </div>
      )}
    </div>
  );
}
