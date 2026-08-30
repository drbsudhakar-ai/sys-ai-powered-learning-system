export function responsibilityRows(coordinators = [], experts = [], faculty = [], subjects = []) {
  const people = new Map(faculty.map((person) => [person.id, person]));
  const subjectMap = new Map(subjects.map((subject) => [subject.id, subject]));
  return [
    ...coordinators.map((assignment) => ({ ...assignment, type: "course_coordinator", responsibility: "Course coordinator", subject_name: "All course subjects", faculty: people.get(assignment.faculty_id) || null })),
    ...experts.map((assignment) => {
      const subject = subjectMap.get(assignment.subject_id);
      return { ...assignment, type: "subject_expert", responsibility: "Subject expert", course_id: assignment.course_id ?? subject?.course_id ?? null, course_title: assignment.course_title || subject?.course_title || "Course not configured", faculty: people.get(assignment.faculty_id) || null };
    }),
  ];
}

export function filterResponsibilities(rows, { search = "", course = "all", type = "all", department = "all" } = {}) {
  const term = search.trim().toLowerCase();
  return rows.filter((row) => {
    if (course !== "all" && String(row.course_id) !== String(course)) return false;
    if (type !== "all" && row.type !== type) return false;
    if (department !== "all" && row.faculty?.department !== department) return false;
    return !term || [row.faculty_name, row.faculty_email, row.faculty?.employee_code, row.faculty?.department, row.course_title, row.subject_name, row.responsibility].filter(Boolean).join(" ").toLowerCase().includes(term);
  }).sort((first, second) => first.course_title.localeCompare(second.course_title) || first.faculty_name.localeCompare(second.faculty_name));
}

export function ownershipSummary(courses = [], subjects = [], coordinators = [], experts = []) {
  const coordinated = new Set(coordinators.map((assignment) => assignment.course_id));
  const covered = new Set(experts.map((assignment) => assignment.subject_id));
  return { coordinators: coordinators.length, experts: experts.length, coursesWithoutCoordinator: courses.filter((course) => !coordinated.has(course.id)).length, subjectsWithoutExpert: subjects.filter((subject) => subject.course_id && !covered.has(subject.id)).length };
}

export function availableFaculty(faculty = []) {
  return faculty.filter((person) => person.is_active !== false && String(person.employment_status || "ACTIVE").toUpperCase() !== "INACTIVE").sort((first, second) => first.name.localeCompare(second.name));
}
