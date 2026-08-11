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

// Auth endpoints
export const registerUser = (data) => API.post("/auth/register", data);
export const loginUser = (data) =>
  API.post("/auth/login", new URLSearchParams(data));
export const getMe = () => API.get("/auth/me");

// Course endpoints
export const getCourses = () => API.get("/courses/");
export const createCourse = (data) => API.post("/courses/", data);

export default API;
