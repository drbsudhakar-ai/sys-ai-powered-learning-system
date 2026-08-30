export function courseReportFilename(response, { scope = "Course", type = "Profile", identifier = "record" } = {}) {
  const disposition = response?.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  if (match?.[1]) return match[1];
  const safe = String(identifier).replace(/[^A-Za-z0-9_-]/g, "_").replace(/^_+|_+$/g, "") || "record";
  return `SYS_${scope === "Subject" ? "Subject" : "Course"}_${type === "Syllabus" ? "Syllabus_Weightages" : "Profile"}_${safe}.pdf`;
}

export function subjectReportRows(experts = []) {
  const seen = new Set();
  return experts.filter((assignment) => {
    if (!assignment?.subject_id || seen.has(assignment.subject_id)) return false;
    seen.add(assignment.subject_id);
    return true;
  });
}
