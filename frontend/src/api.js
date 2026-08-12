import axios from "axios";

const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000",
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getApiErrorMessage(err, fallback = "Something went wrong.") {
  if (!err) return fallback;
  const status = err.response?.status;
  const detail = err.response?.data?.detail;
  if (status === 401) return "Please log in to continue.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "Not found.";
  if (status === 409) return typeof detail === "string" ? detail : "Conflict with existing data.";
  if (status === 422) {
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
    }
    return typeof detail === "string" ? detail : "Please check the form fields and try again.";
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

export const registerUser = (data) => API.post("/auth/register", data);
export const loginUser = (data) =>
  API.post("/auth/login", new URLSearchParams(data));
export const getMe = () => API.get("/auth/me");

export const getCourses = () => API.get("/courses/");
export const getCourse = (id) => API.get(`/courses/${id}`);
export const createCourse = (data) => API.post("/courses/", data);
export const updateCourse = (id, data) => API.put(`/courses/${id}`, data);
export const deleteCourse = (id) => API.delete(`/courses/${id}`);

// Admin — Students
export const adminListStudents = () => API.get("/admin/students");
export const adminGetStudent = (id) => API.get(`/admin/students/${id}`);
export const adminCreateStudent = (data) => API.post("/admin/students", data);
export const adminUpdateStudent = (id, data) => API.put(`/admin/students/${id}`, data);
export const adminDeactivateStudent = (id) => API.post(`/admin/students/${id}/deactivate`);
export const adminActivateStudent = (id) => API.post(`/admin/students/${id}/activate`);

// Admin — Faculty
export const adminListFaculty = () => API.get("/admin/faculty");
export const adminGetFaculty = (id) => API.get(`/admin/faculty/${id}`);
export const adminCreateFaculty = (data) => API.post("/admin/faculty", data);
export const adminUpdateFaculty = (id, data) => API.put(`/admin/faculty/${id}`, data);
export const adminDeactivateFaculty = (id) => API.post(`/admin/faculty/${id}/deactivate`);
export const adminActivateFaculty = (id) => API.post(`/admin/faculty/${id}/activate`);

// Admin — Subjects & responsibilities
export const adminListSubjects = () => API.get("/admin/subjects");
export const adminCreateSubject = (data) => API.post("/admin/subjects", data);
export const adminAssignCourseCoordinator = (data) =>
  API.post("/admin/course-coordinators", data);
export const adminRemoveCourseCoordinator = (id) =>
  API.delete(`/admin/course-coordinators/${id}`);
export const adminAssignSubjectExpert = (data) =>
  API.post("/admin/subject-experts", data);
export const adminRemoveSubjectExpert = (id) =>
  API.delete(`/admin/subject-experts/${id}`);

export default API;
