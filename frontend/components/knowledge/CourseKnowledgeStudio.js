import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useState } from "react";
import { commitExternalKnowledgeImport, createCourseTeachingPackRevision, decideCourseTeachingPack, getApiErrorMessage, getCourseKnowledgeStudio, getExternalKnowledgeTemplate, previewExternalKnowledgeImport, saveSubjectDeliveryGuide } from "../../src/api";
import styles from "./CourseKnowledgeStudio.module.css";

const lines = (value) => Array.isArray(value) ? value.join("\n") : "";
const list = (value) => String(value || "").split("\n").map((item) => item.trim()).filter(Boolean);
const defaultPolicy = { audience: "", teaching_objective: "", default_language: "en-IN", required_lesson_stages: "Introduction\nConcept explanation\nWorked example\nGuided practice\nRecap", delivery_requirements: "Explain conversationally\nShow reasoning step by step\nCheck learner understanding", accuracy_requirements: "Use approved knowledge packages only\nNever invent facts, formulas, or citations" };
const defaultGuide = { teaching_strategy: "Concept → explanation → worked example → guided practice → recap", required_stage_types: "INTRODUCTION\nCONCEPT\nEXPLANATION\nEXAMPLE\nGUIDED_PRACTICE\nRECAP", example_rules: "Use syllabus-aligned examples\nShow every reasoning step", narration_rules: "Explain ideas conversationally\nRead symbols in natural language\nDo not merely read board text", visual_rules: "Use diagrams, tables, timelines, or worked boards when useful", assessment_rules: "Ask a diagnostic question\nInclude guided and independent practice", accuracy_constraints: "Use verified sources only\nRecheck facts, dates, and calculations" };

function Field({ label, value, onChange, area = true, wide = false }) {
  const Tag = area ? "textarea" : "input";
  return <label className={`${styles.field} ${wide ? styles.wide : ""}`}>{label}<Tag value={value || ""} onChange={(event) => onChange(event.target.value)} /></label>;
}

export default function CourseKnowledgeStudio({ courseId, canActivate, backHref }) {
  const router = useRouter();
  const [studio, setStudio] = useState(null); const [policy, setPolicy] = useState(defaultPolicy);
  const [guides, setGuides] = useState({}); const [busy, setBusy] = useState("");
  const [error, setError] = useState(""); const [success, setSuccess] = useState("");
  const [importPayload, setImportPayload] = useState(null); const [importPreview, setImportPreview] = useState(null);
  const load = useCallback(async () => {
    if (!courseId) return;
    const { data } = await getCourseKnowledgeStudio(courseId); setStudio(data);
    const saved = data.teaching_pack?.course_policy;
    if (saved) setPolicy({ ...saved, required_lesson_stages: lines(saved.required_lesson_stages), delivery_requirements: lines(saved.delivery_requirements), accuracy_requirements: lines(saved.accuracy_requirements) });
    const next = {}; (data.subjects || []).forEach((subject) => { const guide = subject.delivery_guide; next[subject.subject_id] = guide ? { ...guide, teaching_strategy: typeof guide.teaching_strategy === "string" ? guide.teaching_strategy : guide.teaching_strategy?.sequence || JSON.stringify(guide.teaching_strategy), required_stage_types: lines(guide.required_stage_types), example_rules: lines(guide.example_rules), narration_rules: lines(guide.narration_rules), visual_rules: lines(guide.visual_rules), assessment_rules: lines(guide.assessment_rules), accuracy_constraints: lines(guide.accuracy_constraints) } : { ...defaultGuide }; }); setGuides(next);
  }, [courseId]);
  useEffect(() => { load().catch((requestError) => setError(getApiErrorMessage(requestError, "Unable to load Course Knowledge Studio."))); }, [load]);

  async function savePolicy() {
    setBusy("policy"); setError(""); setSuccess("");
    try { await createCourseTeachingPackRevision(courseId, { language: "en-IN", course_policy: { ...policy, required_lesson_stages: list(policy.required_lesson_stages), delivery_requirements: list(policy.delivery_requirements), accuracy_requirements: list(policy.accuracy_requirements) }, revision_notes: "Course Knowledge Studio revision" }); await load(); setSuccess("Course Delivery Policy revision saved."); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to save the course policy.")); } finally { setBusy(""); }
  }
  async function saveGuide(subject) {
    setBusy(`guide-${subject.subject_id}`); setError(""); setSuccess(""); const guide = guides[subject.subject_id];
    try { await saveSubjectDeliveryGuide({ subject_id: subject.subject_id, language: "en-IN", teaching_strategy: { sequence: guide.teaching_strategy }, required_stage_types: list(guide.required_stage_types), example_rules: list(guide.example_rules), narration_rules: list(guide.narration_rules), visual_rules: list(guide.visual_rules), assessment_rules: list(guide.assessment_rules), accuracy_constraints: list(guide.accuracy_constraints) }); await load(); setSuccess(`${subject.subject_name} Delivery Guide saved.`); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to save the Subject Delivery Guide.")); } finally { setBusy(""); }
  }
  async function decide(action) {
    const revision = studio?.teaching_pack?.current_revision; if (!revision) { setError("Save the Course Delivery Policy first."); return; }
    setBusy(action); setError(""); setSuccess("");
    try { await decideCourseTeachingPack(courseId, revision, { action, comment: action === "ACTIVATE" ? "Administrator activated the governed teaching pack." : "Validated course policy and all subject delivery guides." }); await load(); setSuccess(action === "ACTIVATE" ? "Teaching Pack activated." : "Teaching Pack validation completed."); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to complete the Teaching Pack decision.")); await load().catch(() => {}); } finally { setBusy(""); }
  }
  function changeGuide(id, field, value) { setGuides((current) => ({ ...current, [id]: { ...(current[id] || defaultGuide), [field]: value } })); }
  async function downloadTemplate() {
    setBusy("template"); setError("");
    try { const { data } = await getExternalKnowledgeTemplate(courseId); const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `SYS-course-${courseId}-knowledge-package-template.json`; anchor.click(); URL.revokeObjectURL(url); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to download the import template.")); } finally { setBusy(""); }
  }
  async function readImportFile(event) {
    setError(""); setSuccess(""); setImportPreview(null); const file = event.target.files?.[0]; if (!file) return;
    try { const parsed = JSON.parse(await file.text()); setImportPayload({ import_name: parsed.import_name, source: parsed.source, packages: parsed.packages }); setSuccess(`${file.name} loaded. Preview validation is required before import.`); }
    catch { setImportPayload(null); setError("The selected file is not valid JSON."); }
  }
  async function previewImport() {
    if (!importPayload) return; setBusy("preview"); setError("");
    try { const { data } = await previewExternalKnowledgeImport(courseId, importPayload); setImportPreview(data); if (data.valid) setSuccess(`Preview passed for ${data.package_count} package(s).`); else setError(data.errors.join(" ")); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to validate the import.")); } finally { setBusy(""); }
  }
  async function commitImport() {
    if (!importPayload || !importPreview?.valid) return; const confirmation = window.prompt("Record the administrator verification and import decision (minimum 5 characters):"); if (!confirmation) return;
    setBusy("import"); setError("");
    try { const { data } = await commitExternalKnowledgeImport(courseId, { ...importPayload, preview_hash: importPreview.preview_hash, confirmation }); setImportPayload(null); setImportPreview(null); await load(); setSuccess(`${data.imported} knowledge package revision(s) imported as governed drafts.`); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to commit the external import.")); } finally { setBusy(""); }
  }
  if (!studio) return <main className={styles.workspace}>{error || "Loading Course Knowledge Studio…"}</main>;
  const c = studio.coverage; const report = studio.teaching_pack?.validation_report || {};
  return <main className={styles.workspace}><Link className={styles.back} href={backHref}>← Back to course</Link><section className={styles.hero}><span className={styles.eyebrow}>PROFESSOR-GRADE LEARNING FOUNDATION</span><h1>{studio.course.title} Knowledge Studio</h1><p>Govern how SYS teaches this course. The active Teaching Pack combines one Course Delivery Policy with one Subject Delivery Guide for every subject.</p></section>{error && <div className={styles.error} role="alert">{error}</div>}{success && <div className={styles.success}>{success}</div>}
  <section className={styles.metrics}><article className={styles.metric}><span>Subjects</span><strong>{c.subjects}</strong><small>Delivery guides: {studio.subjects.filter((x) => x.delivery_guide).length}</small></article><article className={styles.metric}><span>Topics</span><strong>{c.topics}</strong><small>{c.topic_packages} knowledge packages</small></article><article className={styles.metric}><span>Subtopics</span><strong>{c.subtopics}</strong><small>{c.covered_subtopics} covered</small></article><article className={styles.metric}><span>Teaching Pack</span><strong>{studio.teaching_pack?.status || "NOT STARTED"}</strong><small>{studio.access_mode.replaceAll("_", " ")}</small></article></section>
  <section className={styles.card}><h2>1. Course Delivery Policy</h2><p>These are course-wide expectations applied to every generated or uploaded lesson.</p><div className={styles.grid}><Field label="Learner audience" value={policy.audience} onChange={(v) => setPolicy({ ...policy, audience: v })} /><Field label="Default language" area={false} value={policy.default_language} onChange={(v) => setPolicy({ ...policy, default_language: v })} /><Field label="Teaching objective" wide value={policy.teaching_objective} onChange={(v) => setPolicy({ ...policy, teaching_objective: v })} /><Field label="Required lesson stages (one per line)" value={policy.required_lesson_stages} onChange={(v) => setPolicy({ ...policy, required_lesson_stages: v })} /><Field label="Delivery requirements (one per line)" value={policy.delivery_requirements} onChange={(v) => setPolicy({ ...policy, delivery_requirements: v })} /><Field label="Accuracy requirements (one per line)" wide value={policy.accuracy_requirements} onChange={(v) => setPolicy({ ...policy, accuracy_requirements: v })} /></div><div className={styles.actions}><button className={styles.primary} onClick={savePolicy} disabled={Boolean(busy)}>{busy === "policy" ? "Saving…" : "Save new policy revision"}</button></div></section>
  <section className={styles.card}><h2>2. Subject Delivery Guides</h2><p>Keep subject-specific pedagogy without requiring faculty to author every topic package.</p>{studio.subjects.map((subject) => { const guide = guides[subject.subject_id] || defaultGuide; return <details className={styles.subject} key={subject.subject_id}><summary><span>{subject.subject_name}</span><span className={styles.status}>{subject.delivery_guide?.status || "NOT PREPARED"}</span></summary><div className={styles.grid}><Field label="Teaching sequence" wide value={guide.teaching_strategy} onChange={(v) => changeGuide(subject.subject_id, "teaching_strategy", v)} /><Field label="Required stages" value={guide.required_stage_types} onChange={(v) => changeGuide(subject.subject_id, "required_stage_types", v)} /><Field label="Example rules" value={guide.example_rules} onChange={(v) => changeGuide(subject.subject_id, "example_rules", v)} /><Field label="Narration rules" value={guide.narration_rules} onChange={(v) => changeGuide(subject.subject_id, "narration_rules", v)} /><Field label="Visual teaching rules" value={guide.visual_rules} onChange={(v) => changeGuide(subject.subject_id, "visual_rules", v)} /><Field label="Assessment rules" value={guide.assessment_rules} onChange={(v) => changeGuide(subject.subject_id, "assessment_rules", v)} /><Field label="Accuracy constraints" value={guide.accuracy_constraints} onChange={(v) => changeGuide(subject.subject_id, "accuracy_constraints", v)} /></div><button className={styles.primary} onClick={() => saveGuide(subject)} disabled={Boolean(busy)}>{busy === `guide-${subject.subject_id}` ? "Saving…" : `Save ${subject.subject_name} guide`}</button></details>; })}</section>
  <section className={styles.card}><h2>3. Validate and activate</h2><p>Validation requires a complete Course Delivery Policy and one guide for every current subject.</p>{report.errors?.length > 0 && <ul className={styles.validation}>{report.errors.map((item) => <li key={item}>{item}</li>)}</ul>}<div className={styles.actions}><button className={styles.secondary} onClick={() => decide("VALIDATE")} disabled={Boolean(busy)}>Validate Teaching Pack</button>{canActivate ? <button className={styles.primary} onClick={() => decide("ACTIVATE")} disabled={Boolean(busy)}>Activate Teaching Pack</button> : <span className={styles.notice}>Administrator activation is required after coordinator preparation.</span>}</div></section>
  <section className={styles.card}><h2>4. External Knowledge Package Import</h2><p>Import one topic or a governed batch using the course-specific SYS-KP-1.0 JSON template. Nothing is saved until preview validation passes.</p>{canActivate ? <><div className={styles.actions}><button className={styles.secondary} onClick={downloadTemplate} disabled={Boolean(busy)}>{busy === "template" ? "Preparing…" : "Download course template"}</button><label className={styles.secondary}>Select completed JSON<input type="file" accept="application/json,.json" onChange={readImportFile} hidden /></label><button className={styles.secondary} onClick={previewImport} disabled={!importPayload || Boolean(busy)}>{busy === "preview" ? "Validating…" : "Preview and validate"}</button></div>{importPayload && <div className={styles.notice}>{importPayload.import_name || "External import"} · {importPayload.packages?.length || 0} package(s) loaded</div>}{importPreview && <div className={importPreview.valid ? styles.success : styles.error}><strong>{importPreview.valid ? "Validation passed" : "Validation failed"}</strong><p>{importPreview.mapped_packages?.length || 0} topics mapped · {importPreview.warnings?.length || 0} warnings</p>{importPreview.errors?.map((item) => <div key={item}>{item}</div>)}{importPreview.warnings?.map((item) => <div key={item}>{item}</div>)}</div>}<button className={styles.primary} onClick={commitImport} disabled={!importPreview?.valid || Boolean(busy)}>{busy === "import" ? "Importing…" : "Commit governed import"}</button><Link className={styles.secondary} href={`/admin/courses/${courseId}/knowledge-reviews`}>Review imported packages</Link></> : <div className={styles.notice}>External imports are prepared and committed by an administrator. The coordinator can continue monitoring knowledge coverage here.</div>}</section>
  <section className={styles.card}><h2>AI-assisted package generation</h2><p>P036.2C will generate the same governed SYS-KP-1.0 package through configured providers and available limits.</p><button className={styles.secondary} disabled>Coming in P036.2C</button></section></main>;
}
