import axios from "axios";

const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000",
});

// Attach token automatically
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
  if (status === 404) return "Course not found.";
  if (status === 422) {
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
    }
    return "Please check the form fields and try again.";
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

// Auth endpoints
export const registerUser = (data) => API.post("/auth/register", data);
export const loginUser = (data) =>
  API.post("/auth/login", new URLSearchParams(data));
export const getMe = () => API.get("/auth/me");

// Course endpoints
export const getCourses = () => API.get("/courses/");
export const getCourse = (id) => API.get(`/courses/${id}`);
export const createCourse = (data) => API.post("/courses/", data);
export const updateCourse = (id, data) => API.put(`/courses/${id}`, data);
export const deleteCourse = (id) => API.delete(`/courses/${id}`);

export default API;
