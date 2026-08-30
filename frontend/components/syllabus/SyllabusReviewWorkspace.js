import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import { getMe, getApiErrorMessage, getSyllabusReviewWorkspace, startSyllabusReview, getSyllabusReview,
  saveSyllabusReview, actOnSyllabusReview, downloadSyllabusWorkbook, previewSyllabusWorkbook } from "../../src/api";
import { downloadBlob } from "../../src/adminMaster";
import { LEVELS, ordered, reorder, diffNodes, editableReview, parseWorkbook } from "../../src/syllabusReview";
import ApprovedSyllabusDownload from "./ApprovedSyllabusDownload";
import styles from "./SyllabusReview.module.css";
import { courseHomeLink } from "../../src/workspaceNavigation";
import { SYLLABUS_PAGES, syllabusPagePath, subjectBranch } from "../../src/syllabusPages";
import SubjectReviewDashboard from './SubjectReviewDashboard';
import SyllabusDraftActions from './SyllabusDraftActions';

function UploadIcon() {
  return <svg className={styles.uploadIcon} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function FileIcon() {
  return <svg className={styles.fileIcon} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.7" /><path d="M14 3v5h5M8 13h8M8 17h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>;
}

function formatFileSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function Comparison({ changes }) {
  if (!changes.length) return <p>No content changes. An initial baseline can still be submitted for approval.</p>;
  return <div>{changes.map((change) => <article key={change.after.key} className={styles.change}>
    <h4>{change.kind} {change.after.level}: {change.after.name}</h4><div className={styles.compare}>
      <div><strong>Before</strong>{change.before ? <><p>{change.before.name} · Order {change.before.sequence}</p><p>{change.before.description}</p><p>{change.before.learning_outcome}</p></> : <p>New syllabus item</p>}</div>
      <div><strong>Proposed</strong><p>{change.after.name} · Order {change.after.sequence}</p><p>{change.after.description}</p><p>{change.after.learning_outcome}</p></div>
    </div></article>)}</div>;
}

function Tree({ nodes, parent = null, rootKey, editable, manager, onEdit, onAdd, onMove, onRemove }) {
  const siblings = ordered(nodes, parent);
  return <div>{siblings.map((node, index) => {
    if (rootKey && parent === null && node.key !== rootKey) return null;
    const mayEdit = editable && (manager || ["topic", "subtopic"].includes(node.level));
    const next = LEVELS[LEVELS.indexOf(node.level) + 1];
    const mayAdd = editable && next && (manager || ["topic", "subtopic"].includes(next));
    return <details className={styles.node} key={node.key} open={node.level === "subject" || undefined}>
      <summary><span className={styles.tag}>{node.level}</span> {node.sequence}. {node.name}</summary>
      <p>{node.description || "No description added."}</p>{node.learning_outcome && <p><strong>Learning outcome:</strong> {node.learning_outcome}</p>}
      <div className={styles.actions}>{mayEdit && <><button onClick={() => onEdit(node)}>Edit</button><button aria-label={`Move ${node.name} up`} disabled={index === 0} onClick={() => onMove(node.key, -1)}>Move up</button><button aria-label={`Move ${node.name} down`} disabled={index === siblings.length - 1} onClick={() => onMove(node.key, 1)}>Move down</button></>}{mayAdd && <button onClick={() => onAdd(next, node.key)}>Add {next}</button>}</div>
      {mayEdit && node.key.startsWith("new:") && <button onClick={() => onRemove(node.key)}>Remove new item</button>}
      <Tree nodes={nodes} parent={node.key} editable={editable} manager={manager} onEdit={onEdit} onAdd={onAdd} onMove={onMove} onRemove={onRemove} />
    </details>;
  })}</div>;
}

function ApprovedRedirect() {
  const router = useRouter();
  useEffect(() => { if(router.isReady && router.query.id) getMe().then(({data})=>router.replace(courseHomeLink(data.role,router.query.id).href)); },[router.isReady,router.query.id]);
  return <p>Opening course workspace…</p>;
}
export default function SyllabusReviewWorkspace({page = 'structure'}) {
  if(page==='reviews') return <SubjectReviewDashboard/>;
  if(page==='approved') return <ApprovedRedirect/>;
  return <SyllabusAuthoring page={page}/>;
}
function SyllabusAuthoring({ page = "structure" }) {
  const router = useRouter(); const courseId = router.query.id;
  const [data, setData] = useState(null), [review, setReview] = useState(null), [nodes, setNodes] = useState([]);
  const [summary, setSummary] = useState(""), [comment, setComment] = useState(""), [subject, setSubject] = useState("");
  const [error, setError] = useState(""), [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false), [editing, setEditing] = useState(null), [preview, setPreview] = useState(null);
  const [showBaseline, setShowBaseline] = useState(false);
  const [role, setRole] = useState(null), [focusSection, setFocusSection] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [uploadFile, setUploadFile] = useState(null), [uploadStatus, setUploadStatus] = useState("idle"), [dragActive, setDragActive] = useState(false);
  const authoring = page === "structure" || page === "upload";
  const pageTitle = SYLLABUS_PAGES.find(([key]) => key === page)?.[1] || "Syllabus Structure";
  const canEdit = Boolean(review && (data?.can_manage || editableReview(review, data?.actor_id)) && ['DRAFT','CHANGES_REQUESTED'].includes(review.status) && !data?.archived && review.base_revision === data?.revision);
  const mayStructure = data?.can_manage && !review?.subject_id;
  const changes = useMemo(() => diffNodes(review?.base_nodes || [], nodes), [review, nodes]);
  function adopt(row) { setReview(row); setNodes(row.nodes); setSummary(row.summary); setDirty(false); setEditing(null); setPreview(null); setComment(""); setShowBaseline(false); }
  async function refresh() { const res = await getSyllabusReviewWorkspace(courseId); setData(res.data); return res.data; }
  async function run(task) { setBusy(true); setError(""); setMessage(""); try { await task(); } catch (err) { setError(err.response ? getApiErrorMessage(err) : err.message); } finally { setBusy(false); } }
  useEffect(() => {
    if (!router.isReady || !courseId) return;
    let active = true;
    setData(null); setReview(null); setNodes([]); setDirty(false); setEditing(null); setPreview(null); setError(""); setSelectedSubject(""); setUploadFile(null); setUploadStatus("idle"); setDragActive(false);
    Promise.all([getSyllabusReviewWorkspace(courseId), getMe()]).then(async ([{ data: result }, { data: account }]) => {
      if (!active) return; setData(result); setRole(account.role);
      if(!result.can_manage) { router.replace(syllabusPagePath(account.role,courseId,'reviews')); return; }
      const chosen = page !== "approved" && (router.query.review || (authoring && result.reviews.find((r) => ['DRAFT','CHANGES_REQUESTED'].includes(r.status) && r.base_revision === result.revision && !r.subject_id)?.id));
      if (chosen) { const res = await getSyllabusReview(courseId, chosen); if (active) adopt(res.data); }
    }).catch((err) => { if (active) setError(getApiErrorMessage(err)); });
    return () => { active = false; };
  }, [router.isReady, courseId, router.query.review, page]);
  useEffect(() => {
    if (!focusSection) return;
    document.getElementById(focusSection)?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    setFocusSection("");
  }, [focusSection, review]);
  useEffect(() => {
    const warn = (event) => { if (dirty || editing || preview || busy) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, editing, preview, busy]);
  function mayLeave() { return !busy && (!(dirty || editing || preview) || window.confirm("Discard your unsaved changes or upload preview? Save the draft first to keep changes.")); }
  async function open(id) { if (mayLeave()) await run(async () => adopt((await getSyllabusReview(courseId, id)).data)); }
  async function prepareDraft(section) {
    if (editing || (!canEdit && !mayLeave())) return;
    await run(async () => {
      if (!canEdit) {
        const own = data.reviews.find((r) => editableReview(r, data.actor_id) && (data.can_manage ? !r.subject_id : r.subject_id === Number(subject)) && r.base_revision === data.revision);
        if (own) adopt((await getSyllabusReview(courseId, own.id)).data);
        else { adopt((await startSyllabusReview(courseId, { subject_id: data.can_manage ? null : Number(subject) })).data); await refresh(); }
      }
      setFocusSection(section);
    });
  }
  async function save() {
    const res = await saveSyllabusReview(courseId, review.id, { version: review.version, nodes, summary });
    adopt(res.data); await refresh(); return res.data;
  }
  async function action(name) {
    if (["approve", "reject"].includes(name) && !window.confirm(`${name === "approve" ? "Approve and apply" : "Reject"} this complete proposal?`)) return;
    await run(async () => {
      const current = dirty ? await save() : review;
      adopt((await actOnSyllabusReview(courseId, current.id, { version: current.version, action: name, comment })).data);
      await refresh(); setMessage(name === "approve" ? "Approved version saved. Linked learning history is preserved." : "Review status updated.");
    });
  }
  function add(level, parent = null) { setEditing({ key: `new:${crypto.randomUUID()}`, level, parent, name: "", description: "", learning_outcome: "", sequence: Math.max(0, ...ordered(nodes, parent).map((n) => n.sequence)) + 1 }); }
  function saveItem(event) {
    event.preventDefault(); if (!editing.name.trim() || (editing.level !== "subject" && !editing.parent)) return;
    setNodes((old) => old.some((n) => n.key === editing.key) ? old.map((n) => n.key === editing.key ? editing : n) : [...old, editing]);
    if (editing.level === "subject") setSelectedSubject(editing.key);
    setEditing(null); setDirty(true);
  }
  function removeAddition(key) {
    if (!window.confirm("Remove this new draft item and its new descendants? Approved items are never deleted.")) return;
    const removed = new Set([key]);
    for (const level of LEVELS) for (const n of nodes) if (n.level === level && removed.has(n.parent)) removed.add(n.key);
    setNodes(nodes.filter((n) => !removed.has(n.key))); setDirty(true);
  }
  async function workbook(blank) { await run(async () => { if (dirty) throw new Error("Save syllabus before downloading its workbook."); const response = await downloadSyllabusWorkbook(courseId, review.id, blank); downloadBlob(response.data, `SYS_Syllabus_${blank ? "Template" : "Current"}_Course_${Number(courseId)}_v${review.version}.xlsx`); }); }
  async function validateWorkbook(file) {
    if (!file) return;
    setUploadFile({ name: file.name, size: file.size }); setUploadStatus("validating"); setPreview(null); setError(""); setMessage(""); setBusy(true);
    try {
      if (dirty) throw new Error("Save or discard your changes before uploading another workbook.");
      if (!file.name.toLowerCase().endsWith(".xlsx") || file.size > 3 * 1024 * 1024) throw new Error("Select a SYS .xlsx workbook up to 3 MB.");
      const XLSX = await import("xlsx");
      const body = parseWorkbook(XLSX.read(await file.arrayBuffer(), { type: "array", cellFormula: true }), XLSX);
      setPreview((await previewSyllabusWorkbook(courseId, review.id, { ...body, version: review.version })).data);
      setUploadStatus("preview");
    } catch (err) {
      setUploadStatus("error"); setError(err.response ? getApiErrorMessage(err) : err.message);
    } finally { setBusy(false); }
  }
  async function upload(event) {
    const file = event.target.files?.[0]; event.target.value = ""; await validateWorkbook(file);
  }
  async function saveAuthoring() {
    await run(async () => {
      await save();
      if (page === "upload") {
        setUploadStatus("saved");
        setMessage("Syllabus uploaded successfully. It is saved and ready for review and approval.");
      } else setMessage("Syllabus changes saved. Published content is unchanged.");
    });
  }
  const displayNodes = review ? nodes : (data?.nodes || []);
  const subjects = ordered(displayNodes);
  const activeSubject = subjects.find((n) => n.key === selectedSubject)?.key || subjects[0]?.key;
  const branch = subjectBranch(displayNodes, activeSubject);
  const pageHref = (target) => syllabusPagePath(role, courseId, target, review?.id);
  const leavePage = (event) => { if (!mayLeave()) event.preventDefault(); };
  return <main className={styles.workspace}>
    <Head><title>{pageTitle} | SYS</title></Head>
    {role && <Link className={styles.back} href={courseHomeLink(role, courseId).href} onClick={(e) => { if (!mayLeave()) e.preventDefault(); }}>← {courseHomeLink(role, courseId).label}</Link>}
    <header className={styles.hero}><span>SYS · Syllabus management</span><h1>{pageTitle}</h1><p>{data?.course_title || "Loading course…"}</p><p>Strengthen Your Skills · Shape Your Successful Future</p></header>
    {data && <nav className={styles.pageNav} aria-label="Syllabus management pages">{SYLLABUS_PAGES.filter(([key]) => key !== "upload" || data.can_manage).map(([key, label]) => <Link key={key} href={pageHref(key)} aria-current={page === key ? "page" : undefined} onClick={leavePage}>{label}</Link>)}</nav>}
    {error && <div role="alert" className={styles.error}>{error}</div>}{message && <div role="status" className={styles.success}>{message}</div>}
    {!data ? <p>{error ? "Unable to open syllabus review." : "Loading syllabus and academic permissions…"}</p> : <>
      {page === "upload" && !data.can_manage ? <section className={styles.panel}><h2>Excel upload is restricted</h2><p>Only administrators and course coordinators can upload. Propose assigned topic and subtopic changes on Syllabus Structure.</p></section> : <>
      {page === "approved" && <section id="approved-syllabus" className={styles.panel}><h2>Approved syllabus</h2><p>{data.revision ? `Current approved revision: ${data.revision}` : "No approved revision yet. Build or upload a draft, then submit it for approval. PDF downloads become available after approval."}</p>
        {data.revision > 0 && <ApprovedSyllabusDownload courseId={courseId} />}
        <details><summary>Approved version history</summary>{data.revisions.map((v) => <div key={v.number} className={styles.version}><span>Revision {v.number} · {new Date(v.approved_at).toLocaleString()} · {v.summary}</span><ApprovedSyllabusDownload courseId={courseId} revision={v.number} label={`Download revision ${v.number}`} /></div>)}</details>
        {data.revision > 0 && <Tree nodes={data.nodes} />}
      </section>}
      {page !== "approved" && <>
      {page === 'structure' && review && data.can_manage && <SyllabusDraftActions courseId={courseId} review={{...review,nodes}} subjectKey={activeSubject} disabled={dirty||busy||!!editing||!!preview} canReset={canEdit&&data.revision===0} onReset={async row=>{adopt(row);await refresh();setMessage('Unapproved syllabus cleared successfully. Upload a new workbook or create the syllabus manually.');}}/>}
      {authoring && !canEdit && <section className={styles.setupPanel}><h2>{page === "structure" ? "Build your syllabus" : "Prepare your workbook"}</h2><p>{page === "structure" ? "Add subjects, then organize their units, topics and subtopics." : "Prepare an editing copy to download the course-specific template and upload your syllabus."}</p>
        {!data.can_manage && <label>Assigned subject<select value={subject} onChange={(e) => setSubject(e.target.value)}><option value="">Select subject</option>{data.nodes.filter((n) => n.level === "subject").map((n) => <option key={n.key} value={n.key.split(":")[1]}>{n.name}</option>)}</select></label>}
        <button className={styles.primary} disabled={busy || data.archived || (!data.can_manage && !subject)} onClick={() => prepareDraft(page === "upload" ? "syllabus-excel" : "syllabus-structure")}>{page === "structure" ? "Start editing" : "Prepare upload"}</button>
        {data.archived && <p>This course is archived. Syllabus pages are read-only.</p>}
      </section>}
      <div className={page === "upload" ? styles.singleColumn : styles.layout}>
      {page === "reviews" && <aside id="syllabus-reviews" className={styles.panel}><h2>Reviews & approvals</h2>
        <Link href={pageHref("structure")} onClick={leavePage}>Open syllabus authoring</Link>
        {data.archived && <p>This course is archived. Reviews are read-only.</p>}
        <p>{data.can_manage ? "Manage course structure and decide submitted faculty proposals." : "Add, edit and reorder topics/subtopics in your assigned subjects. Coordinator approval is required."}</p>
        {data.reviews.map((r) => <button key={r.id} className={`${styles.review} ${review?.id === r.id ? styles.selected : ""}`} disabled={busy} onClick={() => open(r.id)}><strong>Review #{r.id} · {r.status.replaceAll("_", " ")}</strong><span>{r.author_name}</span><small>{r.summary || "Draft syllabus review"}</small></button>)}
      </aside>}
      {page === "structure" && <aside className={styles.panel}><h2>Subjects <span className={styles.tag}>{subjects.length}</span></h2>{canEdit && mayStructure && <button className={styles.primary} disabled={busy || !!editing} onClick={() => add("subject")}>Add subject</button>}{subjects.map((n) => <button key={n.key} className={`${styles.review} ${activeSubject === n.key ? styles.selected : ""}`} aria-pressed={activeSubject === n.key} disabled={!!editing || busy} onClick={() => setSelectedSubject(n.key)}>{n.sequence}. {n.name}</button>)}{!subjects.length && <p>No subjects added yet.</p>}</aside>}
      <section className={styles.panel}>{!review ? <><h2>{page === "reviews" ? "Select a proposal" : pageTitle}</h2><p>{page === "reviews" ? "Select a review to compare changes and decide on approval." : "Use the button above to begin."}</p>{page === "structure" && <Tree nodes={data.nodes} rootKey={activeSubject} />}</> : <>
        {page === "reviews" && <>
        <h2>Review #{review.id} <span className={styles.tag}>{review.status.replaceAll("_", " ")}</span></h2><p>{review.author_name} · Based on revision {review.base_revision} · Draft version {review.version}{dirty ? " · Unsaved changes" : " · Saved"}</p>
        </>}
        {review.base_revision !== data.revision && !["APPROVED", "REJECTED"].includes(review.status) && <div className={styles.error}>{page === "reviews" ? "The syllabus has changed since this review began. Start a new review and reconcile these changes before submission." : "This editing copy is outdated. Start editing a current copy before making changes."}</div>}
        {page === "reviews" && review.decision_comment && <div className={styles.notice}><strong>Coordinator decision:</strong> {review.decision_comment}<p>{review.decided_by_name}</p></div>}
        {page === "reviews" && <label>Review summary / reason<textarea value={summary} maxLength={1000} disabled={!canEdit || busy} onChange={(e) => { setSummary(e.target.value); setDirty(true); }} /></label>}
        {authoring && <div className={styles.authoringHeading}><div><h2>{page === "upload" ? "Import syllabus from Excel" : subjects.find((n) => n.key === activeSubject)?.name || "Syllabus structure"}</h2><span className={styles.saveState} role="status">{!canEdit ? "Read-only" : page !== "upload" ? dirty ? "Unsaved changes" : "Saved" : uploadStatus === "validating" ? "Validating workbook…" : uploadStatus === "preview" ? "Preview ready" : uploadStatus === "applied" ? "Ready to save" : uploadStatus === "saved" ? "Upload completed" : uploadStatus === "error" ? "Validation failed" : "No workbook selected"}</span></div>{canEdit && <button className={styles.primary} disabled={busy || !!editing || !!preview || !dirty || (page === "upload" && uploadStatus !== "applied")} onClick={saveAuthoring}>Save syllabus</button>}</div>}
        {page === "reviews" && canEdit && <div className={styles.actions}><button className={styles.primary} disabled={busy || !!editing || !!preview} onClick={() => run(async () => { await save(); setMessage("Draft saved. The approved syllabus is unchanged."); })}>Save draft</button><button disabled={busy || !!editing || !summary.trim()} onClick={() => action("submit")}>Save & submit for approval</button></div>}
        {page === "upload" && canEdit && data.can_manage && <section id="syllabus-excel" className={styles.uploadSteps}><article><span className={styles.stepNumber}>1</span><h3>Download a workbook</h3><p>Four sheets: Subjects, Units, Topics and Subtopics. Enter each description once; keep the template headers unchanged.</p><div className={styles.actions}><button disabled={busy || dirty || !!editing} onClick={() => workbook(true)}>Download blank template</button><button disabled={busy || dirty || !!editing} onClick={() => workbook(false)}>Download current syllabus</button></div></article><article><span className={styles.stepNumber}>2</span><h3>Upload and validate</h3><p>Attach a completed SYS workbook and review its validation preview before applying it.</p><div className={`${styles.dropZone} ${dragActive ? styles.dropActive : ""}`} onDragEnter={(e) => { e.preventDefault(); if (!busy && !dirty && !editing) setDragActive(true); }} onDragOver={(e) => e.preventDefault()} onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDragActive(false); }} onDrop={(e) => { e.preventDefault(); setDragActive(false); if (!busy && !dirty && !editing) validateWorkbook(e.dataTransfer.files?.[0]); }} aria-disabled={busy || dirty || !!editing}><UploadIcon /><strong>Drag and drop your workbook here</strong><span>or</span><label className={styles.browseButton} aria-label="Upload workbook">Browse files<input className={styles.fileInput} type="file" accept=".xlsx" disabled={busy || dirty || !!editing} onChange={upload} /></label><small>.xlsx only · maximum 3 MB</small></div>{uploadFile && <div className={styles.fileStatus} role="status"><FileIcon /><div><strong>{uploadFile.name}</strong><small>{formatFileSize(uploadFile.size)} · {uploadStatus === "validating" ? "Validating workbook…" : uploadStatus === "preview" ? "Validation complete — preview ready" : uploadStatus === "applied" ? "Preview completed — content applied" : uploadStatus === "saved" ? "Upload completed successfully" : uploadStatus === "error" ? "Validation failed" : "File attached"}</small></div><span className={uploadStatus === "error" ? styles.statusError : uploadStatus === "saved" ? styles.statusSuccess : styles.statusBadge}>{uploadStatus === "preview" ? "Preview ready" : uploadStatus === "applied" ? "Applied" : uploadStatus === "saved" ? "Saved" : uploadStatus === "error" ? "Action needed" : "Attached"}</span></div>}</article><article><span className={styles.stepNumber}>3</span><h3>Save syllabus</h3>{uploadStatus === "applied" ? <div className={styles.uploadReady} role="status"><strong>Preview completed and content applied.</strong><p>Click <b>Save syllabus</b> to complete the upload.</p></div> : uploadStatus === "saved" ? <div className={styles.uploadComplete} role="status"><strong>Syllabus uploaded successfully.</strong><p>The syllabus is ready for review and approval.</p></div> : <p>Apply the validated content first. Save syllabus will become available when the workbook is ready.</p>}</article></section>}
        {page === "upload" && preview && <section className={styles.notice}><h3>Validation preview · {preview.item_count} items</h3><p>{preview.changes.length} changes detected. Nothing has been saved yet.</p><div className={styles.previewTable}><table><thead><tr><th>Level</th><th>Name</th><th>Description</th></tr></thead><tbody>{preview.nodes.slice(0, 30).map((node) => <tr key={node.key}><td>{node.level}</td><td>{node.name}</td><td>{node.description}</td></tr>)}</tbody></table></div>{preview.nodes.length > 30 && <p>Showing the first 30 items. All {preview.item_count} validated items will be applied.</p>}<div className={styles.actions}><button className={styles.primary} disabled={busy} onClick={() => { setNodes(preview.nodes); setDirty(true); setPreview(null); setUploadStatus("applied"); setMessage(""); }}>Apply validated content</button><button onClick={() => { setPreview(null); setUploadStatus("idle"); setUploadFile(null); }}>Cancel preview</button></div></section>}
        {page === "reviews" && review.status === "SUBMITTED" && !data.archived && <div className={styles.notice}>
          {review.author_id === data.actor_id && <button disabled={busy} onClick={() => action("withdraw")}>Withdraw for editing</button>}
          {data.can_manage && <><p>Review the complete comparison before deciding. Content changes flag affected saved lessons for academic review; they do not regenerate lessons or reset student history.</p><label>Decision comment<textarea value={comment} maxLength={2000} onChange={(e) => setComment(e.target.value)} /></label><div className={styles.actions}><button className={styles.primary} disabled={busy || !comment.trim()} onClick={() => action("approve")}>Approve complete proposal</button><button disabled={busy || !comment.trim()} onClick={() => action("request_changes")}>Request changes</button><button disabled={busy || !comment.trim()} onClick={() => action("reject")}>Reject</button></div></>}
        </div>}
        {page === "reviews" && <details open className={styles.import}><summary>Change comparison · {changes.length} items</summary><Comparison changes={changes} /></details>}
        {page !== "upload" && <>
        {page === "reviews" && <><div className={styles.actions}><button onClick={() => setShowBaseline(!showBaseline)}>{showBaseline ? "Show proposed syllabus" : "Show original baseline"}</button></div><h3>{showBaseline ? "Original baseline" : "Proposed syllabus"}</h3></>}
        <p id="syllabus-structure" className={styles.structureCounts}>{LEVELS.filter((level) => page === "reviews" || level !== "subject").map((level) => `${(page === "structure" ? branch : nodes).filter((n) => n.level === level).length} ${level === "subject" ? "subjects" : level === "unit" ? "units" : level === "topic" ? "topics" : "subtopics"}`).join(" · ")}</p>
        {page === "structure" && canEdit && !showBaseline && <div className={styles.actions}>{LEVELS.filter((level) => level !== "subject" && (mayStructure || ["topic", "subtopic"].includes(level))).map((level) => <button key={level} disabled={busy || !!editing || !branch.some((n) => n.level === LEVELS[LEVELS.indexOf(level) - 1])} onClick={() => add(level, level === "unit" ? activeSubject : "")}>Add {level}</button>)}</div>}
        {!nodes.length && !editing && <div className={styles.emptyState}><h3>Start with your first subject</h3><p>Add its name and description, then build the units, topics and subtopics.</p></div>}
        {editing && <form className={styles.editor} onSubmit={saveItem}>
          <h3>{nodes.some((n) => n.key === editing.key) ? "Edit" : "Add"} {editing.level}</h3>
          {editing.level !== "subject" && !nodes.some((n) => n.key === editing.key) && <label>Parent {LEVELS[LEVELS.indexOf(editing.level) - 1]}<select required value={editing.parent || ""} onChange={(e) => setEditing({ ...editing, parent: e.target.value, sequence: Math.max(0, ...ordered(nodes, e.target.value).map((n) => n.sequence)) + 1 })}><option value="">Select parent</option>{branch.filter((n) => n.level === LEVELS[LEVELS.indexOf(editing.level) - 1]).map((n) => { const path = []; let current = n; while (current) { path.unshift(current.name); current = nodes.find((item) => item.key === current.parent); } return <option key={n.key} value={n.key}>{path.join(" / ")}</option>; })}</select></label>}
          <label>Name<input autoFocus required maxLength={200} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></label>
          <label>Description<textarea maxLength={500} value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></label>
          {editing.level === "unit" && <label>Learning outcome<textarea maxLength={500} value={editing.learning_outcome} onChange={(e) => setEditing({ ...editing, learning_outcome: e.target.value })} /></label>}
          <div className={styles.actions}><button className={styles.primary} type="submit">Apply changes</button><button type="button" onClick={() => setEditing(null)}>Cancel</button></div><p className={styles.saveState}>Use Save syllabus after applying your changes.</p>
        </form>}
        <Tree nodes={showBaseline ? review.base_nodes : nodes} rootKey={page === "structure" ? activeSubject : undefined} editable={page === "structure" && canEdit && !busy && !showBaseline && !editing} manager={mayStructure} onEdit={setEditing} onAdd={add} onRemove={removeAddition} onMove={(key, direction) => { setNodes(reorder(nodes, key, direction)); setDirty(true); }} />
        </>}
        {page === "reviews" && <details className={styles.import}><summary>Review audit history</summary>{review.history?.map((entry, i) => <p key={i}>{entry.action.replace("syllabus.", "").replaceAll("_", " ")} · {new Date(entry.at).toLocaleString()}{entry.details?.comment ? ` · ${entry.details.comment}` : ""}</p>)}</details>}
      </>}</section></div></>}
      </>}
    </>}
  </main>;
}
