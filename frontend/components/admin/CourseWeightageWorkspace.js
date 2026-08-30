import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeftIcon, ArrowPathIcon, BookmarkSquareIcon, ScaleIcon } from "@heroicons/react/24/outline";
import { getAdminOperationsSummary, getApiErrorMessage, getCourseAcademicWeightages, updateCourseAcademicWeightages } from "../../src/api";
import { equalDistribution, groupPayload, groupState, groupTotal, WEIGHTAGE_LEVELS, weightageGroups, weightageReadiness } from "../../src/academicWeightages";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./CourseWeightageWorkspace.module.css";

function Metric({ label, value, detail }) {
  return <article className={styles.metric}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function WeightageGroup({ group, drafts, setDrafts, onSave, saving }) {
  const values = drafts[group.key] || {};
  const total = groupTotal(group.items, values);
  const state = groupState(group.items, values);
  const level = WEIGHTAGE_LEVELS.find((item) => item.value === group.level);
  const dirty = Object.keys(values).length > 0;
  const badge = state === "complete" ? styles.statusComplete : state === "invalid" ? styles.statusInvalid : styles.statusPending;
  const status = state === "complete" ? "100% configured" : state === "invalid" ? `${total}% · adjust total` : "Not configured";

  function update(itemId, value) {
    setDrafts((previous) => ({ ...previous, [group.key]: { ...(previous[group.key] || {}), [itemId]: value } }));
  }

  return <article className={styles.group}><header className={styles.groupHeader}><div><h2>{level.label} · {group.parent_name}</h2><p>{group.items.length} {level.label.toLowerCase()} must total 100% within this {level.parentLabel.toLowerCase()}.</p></div><span className={badge}>{status}</span></header><div className={styles.rows}>{group.items.map((item) => <div key={item.id} className={styles.row}><div><strong>{item.name}</strong><small>{item.sequence ? `Unit sequence ${item.sequence}` : level.value === "subject" ? "Course-level subject weightage" : `${level.value.charAt(0).toUpperCase()}${level.value.slice(1)}-level academic importance`}</small></div><label className={styles.inputWrap}><input aria-label={`${item.name} ${level.value} weightage percentage`} type="number" min="0" max="100" step="0.01" value={values[item.id] ?? item.weight_percent ?? ""} placeholder="0.00" onChange={(event) => update(item.id, event.target.value)} disabled={!group.editable || saving} /><span>%</span></label></div>)}</div><footer className={styles.groupFooter}><strong className={state === "complete" ? styles.totalComplete : styles.totalInvalid}>Total: {total.toFixed(2)}% / 100%</strong><div className={styles.actions}><button type="button" className={styles.subtleButton} onClick={() => setDrafts((previous) => ({ ...previous, [group.key]: equalDistribution(group.items) }))} disabled={!group.editable || saving}>Distribute equally</button><button type="button" className={styles.primary} onClick={() => onSave(group, values)} disabled={!group.editable || !dirty || state !== "complete" || saving}><BookmarkSquareIcon />{saving ? "Saving…" : "Save weightages"}</button></div></footer>{!group.editable && <div className={styles.scope}>Only an assigned subject expert, course coordinator, or administrator can update this group.</div>}</article>;
}

export default function CourseWeightageWorkspace() {
  const router = useRouter();
  const access = useAdminAccess();
  const courseId = router.query.id;
  const [tree, setTree] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("all");
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [drafts, setDrafts] = useState({});

  const refresh = useCallback(async () => {
    if (!courseId) return;
    const response = await getCourseAcademicWeightages(courseId);
    if (!response.data || !Array.isArray(response.data.subjects)) throw new Error("SYS returned an invalid academic weightage response.");
    setTree(response.data);
  }, [courseId]);

  useEffect(() => {
    if (access.status !== "ready" || !router.isReady || !courseId) return undefined;
    let current = true;
    setLoading(true); setError("");
    refresh().catch((requestError) => { if (current) setError(getApiErrorMessage(requestError, "Unable to load academic weightages.")); }).finally(() => { if (current) setLoading(false); });
    getAdminOperationsSummary().then(({ data }) => { if (current) setSummary(data || null); }).catch(() => {});
    return () => { current = false; };
  }, [access.status, courseId, refresh, router.isReady]);

  const groups = useMemo(() => weightageGroups(tree).filter((group) => group.items.length), [tree]);
  const readiness = useMemo(() => weightageReadiness(tree), [tree]);
  const visible = useMemo(() => groups.filter((group) => {
    if (levelFilter !== "all" && group.level !== levelFilter) return false;
    if (subjectFilter !== "all" && group.level !== "subject" && String(group.subject_id) !== String(subjectFilter)) return false;
    const query = search.trim().toLowerCase();
    return !query || [group.parent_name, ...group.items.map((item) => item.name)].join(" ").toLowerCase().includes(query);
  }), [groups, levelFilter, subjectFilter, search]);

  async function save(group, values) {
    setSavingKey(group.key); setError(""); setSuccess("");
    try { await updateCourseAcademicWeightages(courseId, groupPayload(group, values)); await refresh(); setDrafts((previous) => { const next = { ...previous }; delete next[group.key]; return next; }); setSuccess(`${WEIGHTAGE_LEVELS.find((item) => item.value === group.level).label} weightages saved for ${group.parent_name}.`); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "Unable to save academic weightages.")); }
    finally { setSavingKey(""); }
  }

  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing the SYS academic weightage workspace." />;
  if (access.status === "error") return <BrandedState type="error" title="Academic weightages unavailable" message={access.error} />;
  if (access.status !== "ready") return null;

  return <><Head><title>{tree?.course_title || "Course"} Weightages | SYS</title><meta name="description" content="Configure approved SYS subject, unit, topic, and subtopic academic weightages." /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head><AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} breadcrumb="Academic Management" pageTitle="Academic Weightages" scopeLabel={summary?.scope_label || "Platform-wide"}><main className={styles.workspace}><Link href={courseId ? `/admin/courses/${courseId}` : "/admin/courses"} className={styles.back}><ArrowLeftIcon />Back to course profile</Link><header className={styles.heading}><div><span className={styles.eyebrow}>Academic management · Examination intelligence</span><h1>{tree?.course_title || "Course"} Academic Weightages</h1><p>Set approved academic importance for every course, subject, unit, topic, and subtopic group.</p></div><div className={styles.actions}><button type="button" className={styles.button} disabled={loading || Boolean(savingKey)} onClick={() => { setLoading(true); refresh().catch((requestError) => setError(getApiErrorMessage(requestError, "Unable to refresh academic weightages."))).finally(() => setLoading(false)); }}><ArrowPathIcon />Refresh</button><Link href={`/admin/courses/${courseId}/syllabus`} className={styles.button}><ScaleIcon />Manage syllabus</Link></div></header>
    <section className={styles.metrics}><Metric label="Subject weightages" value={tree?.configured?.subjects || 0} detail={`${tree?.subjects?.length || 0} course subjects available`} /><Metric label="Unit weightages" value={tree?.configured?.units || 0} detail="Configured within each subject" /><Metric label="Topic and subtopic weightages" value={(tree?.configured?.topics || 0) + (tree?.configured?.subtopics || 0)} detail="Detailed learning priorities" /><Metric label="Weightage readiness" value={`${readiness.percent}%`} detail={`${readiness.completed} of ${readiness.groups} groups complete`} /></section>
    <div className={styles.notice}>Every sibling group is saved independently and must equal exactly 100%. These weightages support future assessment blueprints, learning prioritization, and question intelligence.</div>{error && <div className={styles.error} role="alert">{error}</div>}{success && <div className={styles.success} role="status">{success}</div>}
    <div className={styles.layout}><section className={styles.panel}><div className={styles.toolbar}><input aria-label="Search academic weightages" className={styles.search} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search subject, unit, topic, or subtopic" /><select aria-label="Filter weightage level" className={styles.select} value={levelFilter} onChange={(event) => setLevelFilter(event.target.value)}><option value="all">All hierarchy levels</option>{WEIGHTAGE_LEVELS.map((level) => <option key={level.value} value={level.value}>{level.label}</option>)}</select><select aria-label="Filter subject" className={styles.select} value={subjectFilter} onChange={(event) => setSubjectFilter(event.target.value)}><option value="all">All subjects</option>{(tree?.subjects || []).map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></div>{loading ? <div className={styles.loading}>Loading syllabus hierarchy and saved academic weightages…</div> : !groups.length ? <div className={styles.empty}><h3>No syllabus items available for weightages</h3><p>Add course subjects, units, topics, and subtopics before assigning academic importance.</p><Link href={`/admin/courses/${courseId}/syllabus`} className={styles.primary}>Open syllabus workspace</Link></div> : !visible.length ? <div className={styles.empty}><h3>No weightage groups match the selected filters</h3><p>Adjust the hierarchy, subject, or search filters.</p></div> : visible.map((group) => <WeightageGroup key={group.key} group={group} drafts={drafts} setDrafts={setDrafts} onSave={save} saving={savingKey === group.key} />)}</section>
    <aside className={styles.guidance}><h2>How SYS academic weightages work</h2><p>Assign relative importance within each parent group. Each group must total 100% before it can be saved.</p><div className={styles.hierarchy}><div><strong>Course → Subjects</strong><small>Physics + Chemistry + Biology = 100%</small></div><div><strong>Subject → Units</strong><small>All Physics units together = 100%</small></div><div><strong>Unit → Topics</strong><small>All topics inside one unit = 100%</small></div><div><strong>Topic → Subtopics</strong><small>All subtopics inside one topic = 100%</small></div></div><ul><li>Administrators and course coordinators can manage the entire course.</li><li>Subject experts can update only their assigned subjects.</li><li>Equal distribution provides a safe starting point.</li><li>Every saved change is recorded in the SYS audit trail.</li></ul><div className={styles.scope}>Future learning, assessments, and question-intelligence modules can consume these approved academic priorities.</div></aside></div>
  </main></AdminShell></>;
}
