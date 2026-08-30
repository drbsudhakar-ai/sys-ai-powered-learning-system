export const administratorRole = (role) => ["admin", "super_admin"].includes(String(role || "").toLowerCase());

export function courseListLink(role) {
  if (administratorRole(role)) return { href: "/admin/courses", label: "Back to Course Master" };
  return role === "faculty"
    ? { href: "/faculty/coordinator-courses", label: "Back to Coordinator Courses" }
    : { href: "/courses", label: "Back to My Courses" };
}

export function courseHomeLink(role, courseId) {
  return administratorRole(role)
    ? { href: `/admin/courses/${courseId}`, label: "Back to course profile" }
    : { href: `/courses/${courseId}/workspace`, label: "Back to course workspace" };
}

export function syllabusLink(role, courseId) {
  return administratorRole(role) ? `/admin/courses/${courseId}/syllabus` : `/courses/${courseId}/syllabus`;
}
