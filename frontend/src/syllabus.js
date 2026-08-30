export const SYLLABUS_COLUMNS = ["Subject", "Unit", "Topic", "Subtopic", "Subject Description", "Unit Description", "Topic Description", "Subtopic Description", "Unit Sequence"];
const value = (row, key) => String(row[key] ?? "").trim();
export function normalizeSyllabusRows(rows) {
  const errors = [];
  const normalized = rows.map((row, index) => {
    const item = { subject: value(row,"Subject"), unit: value(row,"Unit"), topic: value(row,"Topic"), subtopic: value(row,"Subtopic") || null, subject_description: value(row,"Subject Description") || null, unit_description: value(row,"Unit Description") || null, topic_description: value(row,"Topic Description") || null, subtopic_description: value(row,"Subtopic Description") || null, unit_sequence: Number(row["Unit Sequence"] || 1) };
    if (!item.subject || !item.unit || !item.topic) errors.push(`Row ${index + 2}: Subject, Unit, and Topic are required.`);
    if (!Number.isInteger(item.unit_sequence) || item.unit_sequence < 1) errors.push(`Row ${index + 2}: Unit Sequence must be a positive whole number.`);
    return item;
  });
  return { rows: normalized, errors };
}
export function syllabusCounts(tree) {
  const subjects=tree?.subjects||[], units=subjects.flatMap(x=>x.units||[]), topics=units.flatMap(x=>x.topics||[]);
  return {subjects:subjects.length,units:units.length,topics:topics.length,subtopics:topics.reduce((n,x)=>n+(x.subtopics?.length||0),0)};
}
