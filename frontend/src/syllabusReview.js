export const LEVELS = ["subject", "unit", "topic", "subtopic"];
export const SHEETS = ["Subjects", "Units", "Topics", "Subtopics"];
export const editableReview = (review, actorId) => Boolean(review && review.author_id === actorId && ["DRAFT", "CHANGES_REQUESTED"].includes(review.status));
export function ordered(nodes, parent = null) {
  return nodes.filter((n) => n.parent === parent).sort((a, b) => a.sequence - b.sequence || a.name.localeCompare(b.name));
}
export function reorder(nodes, key, direction) {
  const item = nodes.find((n) => n.key === key);
  if (!item) return nodes;
  const siblings = ordered(nodes, item.parent);
  const index = siblings.findIndex((n) => n.key === key), target = index + direction;
  if (target < 0 || target >= siblings.length) return nodes;
  [siblings[index], siblings[target]] = [siblings[target], siblings[index]];
  const sequence = new Map(siblings.map((n, i) => [n.key, i + 1]));
  return nodes.map((n) => sequence.has(n.key) ? { ...n, sequence: sequence.get(n.key) } : n);
}
export function diffNodes(before, after) {
  const baseline = new Map(before.map((n) => [n.key, n]));
  return after.flatMap((node) => {
    const old = baseline.get(node.key);
    return !old || ["name", "description", "sequence", "learning_outcome", "parent"].some((f) => old[f] !== node[f]) ? [{ kind: old ? "Updated" : "Added", before: old, after: node }] : [];
  });
}
export function parseWorkbook(book, XLSX) {
  const meta = book.Sheets["SYS Metadata"];
  if (!meta) throw new Error("Use the new SYS workbook downloaded from this review. The old flat template is not supported here.");
  const metadata = Object.fromEntries(XLSX.utils.sheet_to_json(meta, { defval: "" }).map((r) => [String(r.Setting), String(r.Value)]));
  const sheets = {}; let total = 0;
  for (const name of SHEETS) {
    const sheet = book.Sheets[name];
    if (!sheet) throw new Error(`Missing worksheet: ${name}`);
    const range = XLSX.utils.decode_range(sheet["!ref"] || "A1");
    if (range.e.r > 5001 || range.e.c > 12) throw new Error(`${name}: maximum 5,000 rows and standard columns only.`);
    const headers = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" })[0] || [];
    const required = ["Name", "Description", "Order", ...(name !== "Subjects" ? ["Parent"] : []), ...(name === "Units" ? ["Learning outcome"] : []), "SYS Reference"];
    if (required.some((h) => !headers.includes(h)) || new Set(headers).size !== headers.length) throw new Error(`${name}: keep the template headers unchanged.`);
    for (const [address, cell] of Object.entries(sheet)) {
      if (!address.startsWith("!") && cell.f && headers[XLSX.utils.decode_cell(address).c] !== "SYS Path") throw new Error(`${name}!${address}: formulas are not permitted in syllabus inputs.`);
    }
    sheets[name] = XLSX.utils.sheet_to_json(sheet, { defval: "" }).filter((row) => required.some((h) => row[h] !== "")).map((row) => Object.fromEntries(required.map((h) => [h, row[h] ?? ""])));
    total += sheets[name].length;
  }
  if (total > 5000) throw new Error("Maximum 5,000 syllabus items per upload.");
  return { metadata, sheets };
}
