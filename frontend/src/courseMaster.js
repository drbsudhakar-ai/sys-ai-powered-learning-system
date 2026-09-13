export const COURSE_CATEGORIES = [
  { value: "HIGHER_EDUCATION_ENTRANCE", label: "Higher-education entrance" },
  { value: "EMPLOYMENT_EXAM", label: "Employment examination" },
  { value: "INDEPENDENT_LEARNING", label: "Independent learning" },
  { value: "SKILL_DEVELOPMENT", label: "Skill development" },
];

export const COURSE_SETUP_PHASES = [
  { title: "Course foundation", description: "Course identity, examination details, objective, and status." },
  { title: "Syllabus structure", description: "Subjects, units, topics, subtopics, and structured syllabus import." },
  { title: "Academic ownership", description: "Course coordinator and subject-expert responsibilities." },
  { title: "Academic weightages", description: "Faculty-reviewed subject, unit, topic, and subtopic priorities." },
  { title: "Academic integration", description: "Learning, assessments, question intelligence, and student progress." },
];

export function courseCategoryLabel(value) {
  return COURSE_CATEGORIES.find((category) => category.value === value)?.label || "Independent learning";
}

export function isExaminationCourse(category) {
  return ["HIGHER_EDUCATION_ENTRANCE", "EMPLOYMENT_EXAM"].includes(category);
}

export function courseStatusLabel(course) {
  const status = course?.publication_status || (course?.is_active ? "PUBLISHED" : "DRAFT");
  return { DRAFT: "Draft", READY_FOR_REVIEW: "Ready for review", PUBLISHED: "Published", PILOT_PUBLISHED: "Controlled pilot", ARCHIVED: "Archived" }[status] || "Draft";
}

export function courseFormValues(course = {}) {
  return {
    title: course.title || "",
    programme_code: course.programme_code || "",
    programme_category: course.programme_category || "HIGHER_EDUCATION_ENTRANCE",
    examination_name: course.examination_name || "",
    examination_authority: course.examination_authority || "",
    target_purpose: course.target_purpose || "",
    description: course.description || "",
    syllabus_url: course.syllabus_url || "",
    resources_url: course.resources_url || "",
    is_active: course.is_active === true,
  };
}

export function validateCourseForm(form) {
  if (!String(form.title || "").trim()) return "Course title is required.";
  const code = String(form.programme_code || "").trim().toUpperCase();
  if (!code) return "Course code is required.";
  if (!/^[A-Z0-9][A-Z0-9_-]{0,79}$/.test(code)) return "Course code can contain only letters, numbers, hyphens, and underscores.";
  if (!COURSE_CATEGORIES.some(({ value }) => value === form.programme_category)) return "Choose a supported SYS course category.";
  if (code === "ENGLISH_COMMUNICATION" && form.programme_category !== "INDEPENDENT_LEARNING") return "The reserved English Communication course code requires the Independent learning category.";
  if (isExaminationCourse(form.programme_category) && !String(form.examination_name || "").trim()) return "Examination name is required for an examination-preparation course.";
  for (const [field, label] of [["syllabus_url", "Syllabus reference URL"], ["resources_url", "Learning resources URL"]]) {
    const value = String(form[field] || "").trim();
    if (!value) continue;
    try {
      const parsed = new URL(value);
      if (!["http:", "https:"].includes(parsed.protocol)) return `${label} must begin with http:// or https://.`;
    } catch {
      return `${label} must be a valid web address.`;
    }
  }
  return "";
}

export function coursePayload(form) {
  const examination = isExaminationCourse(form.programme_category);
  return {
    title: String(form.title || "").trim(),
    programme_code: String(form.programme_code || "").trim().toUpperCase(),
    programme_category: form.programme_category,
    examination_name: examination ? String(form.examination_name || "").trim() || null : null,
    examination_authority: examination ? String(form.examination_authority || "").trim() || null : null,
    target_purpose: String(form.target_purpose || "").trim() || null,
    description: String(form.description || "").trim() || null,
    syllabus_url: String(form.syllabus_url || "").trim() || null,
    resources_url: String(form.resources_url || "").trim() || null,
    is_active: Boolean(form.is_active),
  };
}

export function filterCourses(courses, { search = "", category = "all", status = "all", sort = "name" } = {}) {
  const term = String(search).trim().toLowerCase();
  const filtered = courses.filter((course) => {
    const searchable = [course.title, course.programme_code, course.examination_name, course.target_purpose, ...(course.course_coordinators || []).map((person) => person.faculty_name)].join(" ").toLowerCase();
    if (term && !searchable.includes(term)) return false;
    if (category !== "all" && course.programme_category !== category) return false;
    if (status === "active" && !course.is_active) return false;
    if (status === "draft" && course.is_active) return false;
    if (status === "needs_attention" && (course.course_coordinators?.length || 0) > 0 && (course.subject_count || 0) > 0) return false;
    return true;
  });
  return filtered.sort((left, right) => {
    if (sort === "recent") return Number(right.id || 0) - Number(left.id || 0);
    if (sort === "students") return Number(right.student_count || 0) - Number(left.student_count || 0);
    return String(left.title || "").localeCompare(String(right.title || ""));
  });
}

export function courseReadiness(course) {
  return [
    { label: "Course identity", complete: Boolean(course?.title && course?.programme_code), detail: course?.programme_code || "Course code not configured." },
    { label: "Academic syllabus", complete: Number(course?.subject_count || 0) > 0, detail: Number(course?.subject_count || 0) > 0 ? `${course.subject_count} subjects configured.` : "No subjects configured yet." },
    { label: "Course coordinator", complete: Boolean(course?.course_coordinators?.length), detail: course?.course_coordinators?.length ? `${course.course_coordinators.length} coordinator assignments.` : "No course coordinator assigned yet." },
    { label: "Student enrollment", complete: Number(course?.student_count || 0) > 0, detail: Number(course?.student_count || 0) > 0 ? `${course.student_count} students enrolled.` : "No students enrolled yet." },
  ];
}

export function courseDateLabel(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }).format(date)} IST`;
}

export function courseCsv(courses) {
  const escape = (value) => {
    let content = String(value ?? "");
    if (/^[=+\-@\t\r]/.test(content)) content = `'${content}`;
    return `"${content.replaceAll('"', '""')}"`;
  };
  const heading = ["Course Code", "Course Title", "Category", "Examination", "Subjects", "Units", "Topics", "Subtopics", "Students Enrolled", "Coordinators", "Status"];
  const rows = courses.map((course) => [course.programme_code || "", course.title, courseCategoryLabel(course.programme_category), course.examination_name || "", course.subject_count || 0, course.unit_count || 0, course.topic_count || 0, course.subtopic_count || 0, course.student_count || 0, (course.course_coordinators || []).map((person) => person.faculty_name).join("; "), courseStatusLabel(course)]);
  return `\uFEFF${[heading, ...rows].map((row) => row.map(escape).join(",")).join("\r\n")}\r\n`;
}
