export const WEIGHTAGE_LEVELS = Object.freeze([
  Object.freeze({ value: "subject", label: "Subjects", parentLabel: "Course" }),
  Object.freeze({ value: "unit", label: "Units", parentLabel: "Subject" }),
  Object.freeze({ value: "topic", label: "Topics", parentLabel: "Unit" }),
  Object.freeze({ value: "subtopic", label: "Subtopics", parentLabel: "Topic" }),
]);

export function weightValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 && number <= 100 ? number : null;
}

export function groupTotal(items = [], values = {}) {
  return Number(items.reduce((sum, item) => sum + (weightValue(values[item.id] ?? item.weight_percent) ?? 0), 0).toFixed(2));
}

export function groupState(items = [], values = {}) {
  if (!items.length) return "empty";
  if (items.some((item) => weightValue(values[item.id] ?? item.weight_percent) === null)) return "incomplete";
  return Math.abs(groupTotal(items, values) - 100) <= 0.01 ? "complete" : "invalid";
}

export function equalDistribution(items = []) {
  if (!items.length) return {};
  const cents = Math.floor(10000 / items.length);
  const remainder = 10000 - cents * items.length;
  return Object.fromEntries(items.map((item, index) => [item.id, ((cents + (index < remainder ? 1 : 0)) / 100).toFixed(2)]));
}

export function weightageGroups(tree) {
  const subjects = Array.isArray(tree?.subjects) ? tree.subjects : [];
  const groups = tree?.can_manage_course === true
    ? [{ key: `subject-${tree?.course_id || 0}`, level: "subject", parent_id: tree?.course_id, parent_name: tree?.course_title || "Course", subject_id: null, items: subjects, editable: true }]
    : [];
  for (const subject of subjects) {
    groups.push({ key: `unit-${subject.id}`, level: "unit", parent_id: subject.id, parent_name: subject.name, subject_id: subject.id, items: subject.units || [], editable: subject.editable !== false });
    for (const unit of subject.units || []) {
      groups.push({ key: `topic-${unit.id}`, level: "topic", parent_id: unit.id, parent_name: `${subject.name} · ${unit.name}`, subject_id: subject.id, items: unit.topics || [], editable: subject.editable !== false });
      for (const topic of unit.topics || []) groups.push({ key: `subtopic-${topic.id}`, level: "subtopic", parent_id: topic.id, parent_name: `${subject.name} · ${unit.name} · ${topic.name}`, subject_id: subject.id, items: topic.subtopics || [], editable: subject.editable !== false });
    }
  }
  return groups;
}

export function weightageReadiness(tree) {
  const groups = weightageGroups(tree).filter((group) => group.items.length);
  const completed = groups.filter((group) => groupState(group.items) === "complete").length;
  if (tree?.pilot) {
    const coveredPercent = Number((tree.subjects || []).reduce((sum, subject) => (
      subject.governance?.complete ? sum + (weightValue(subject.weight_percent) || 0) : sum
    ), 0).toFixed(2));
    return { groups: groups.length, completed, pending: groups.length - completed, percent: coveredPercent, coveredPercent };
  }
  return { groups: groups.length, completed, pending: groups.length - completed, percent: groups.length ? Math.round((completed / groups.length) * 100) : 0 };
}

export function groupPayload(group, values) {
  return { level: group.level, parent_id: Number(group.parent_id), items: group.items.map((item) => ({ item_id: Number(item.id), weight_percent: Number(values[item.id] ?? item.weight_percent) })) };
}

export function pilotGroupPayload(group, values, courseId) {
  return {
    level: group.level,
    parent_key: group.level === "subject" ? `course:${courseId}` : String(group.parent_id),
    items: group.items.map((item) => ({
      item_key: String(item.id),
      weight_percent: Number(values[item.id] ?? item.weight_percent),
    })),
  };
}
