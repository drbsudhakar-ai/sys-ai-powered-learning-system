/**
 * Lightweight auth helpers for Course Management pages.
 * Uses existing token + /auth/me contract (no new auth architecture).
 */

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function clearSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
}

export function isStaffRole(role) {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "faculty";
}

export function redirectToLogin() {
  if (typeof window === "undefined") return;
  window.location.href = "/login";
}
