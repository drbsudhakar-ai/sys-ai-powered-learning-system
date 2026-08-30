export const SYLLABUS_PAGES = [
  ["structure", "Syllabus Structure"], ["upload", "Excel Upload"],
  ["reviews", "Reviews & Approvals"],
];
export function syllabusPagePath(role, courseId, page = "structure", reviewId) {
  const admin = ["admin", "super_admin"].includes(String(role || "").toLowerCase());
  const base = `${admin ? "/admin" : ""}/courses/${courseId}/syllabus`;
  const path = page === "structure" ? base : `${base}/${page}`;
  return reviewId && page !== "approved" ? `${path}?review=${encodeURIComponent(reviewId)}` : path;
}
export function subjectBranch(nodes, subjectKey) {
  const keys = new Set([subjectKey]);
  for (const level of ["unit", "topic", "subtopic"]) {
    for (const node of nodes) if (node.level === level && keys.has(node.parent)) keys.add(node.key);
  }
  return nodes.filter((node) => keys.has(node.key));
}
