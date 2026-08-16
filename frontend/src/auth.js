/**
 * Lightweight auth helpers for Course Management pages.
 * Uses existing token + /auth/me contract (no new auth architecture).
 */

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("token");
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("token");
}

export function setToken(token) {
  if (typeof window === "undefined") return false;
  if (typeof token !== "string" || !token.trim()) {
    clearSession();
    return false;
  }
  window.localStorage.setItem("token", token.trim());
  return true;
}

export const REGISTRATION_ROLES = Object.freeze([
  Object.freeze({ value: "student", label: "Student" }),
  Object.freeze({ value: "faculty", label: "Faculty" }),
]);

export function isStaffRole(role) {
  const r = (role || "").toLowerCase();
  return r === "super_admin" || r === "admin" || r === "faculty";
}

export function isAdminRole(role) {
  const normalized = (role || "").toLowerCase();
  return normalized === "super_admin" || normalized === "admin";
}

export function roleDisplayLabel(role) {
  switch ((role || "").toLowerCase()) {
    case "super_admin":
      return "Super Admin";
    case "admin":
      return "Administrator";
    case "faculty":
      return "Faculty";
    case "student":
      return "Student";
    default:
      return "SYS User";
  }
}

export function roleLandingPath(role) {
  switch ((role || "").toLowerCase()) {
    case "super_admin":
    case "admin":
      return "/admin-dashboard";
    case "faculty":
    case "student":
      return "/dashboard";
    default:
      return null;
  }
}

export function redirectToLogin(reason) {
  if (typeof window === "undefined") return;
  const suffix = reason ? `?reason=${encodeURIComponent(reason)}` : "";
  window.location.href = `/login${suffix}`;
}
