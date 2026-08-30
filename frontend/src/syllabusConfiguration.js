// Manager-only course responses include saved administrative configuration.
// Never derive student learning availability from these draft counts.
export function configuredOwnership(courses, subjects, experts) {
  const configured = courses.filter(c => c.syllabus_configuration);
  const ids = new Set(configured.map(c => String(c.id)));
  return {
    subjects: [...subjects.filter(s => !ids.has(String(s.course_id))), ...configured.flatMap(c => c.syllabus_configuration.subjects)],
    experts: [...experts.filter(e => !ids.has(String(e.course_id))), ...configured.flatMap(c => c.syllabus_configuration.experts)],
  };
}

export function configurationLabel(configuration) {
  if (!configuration) return '';
  return `${configuration.status === 'WORKING_DRAFT' ? 'Saved working syllabus' : 'Configured syllabus'} · ${configuration.approved_subject_count} subjects approved. Approval and publication are separate.`;
}
