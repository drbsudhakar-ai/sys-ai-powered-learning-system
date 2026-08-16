import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AdjustmentsHorizontalIcon,
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import styles from "./MasterWorkspace.module.css";
import {
  adminBulkFacultyAssignment,
  adminBulkFacultyStatus,
  adminBulkStudentStatus,
  adminExportFacultyMaster,
  adminExportStudentMaster,
  adminListFacultyMaster,
  adminListStudentMaster,
  adminListSubjects,
  getAdminOperationsSummary,
  getApiErrorMessage,
  getCourses,
} from "../../src/api";
import { clearSession } from "../../src/auth";
import {
  compactQuery,
  downloadBlob,
  isMasterPageResponse,
  masterQueryFromRouter,
  MASTER_PAGE_SIZES,
  MASTER_STATUS_TABS,
} from "../../src/adminMaster";

const CONFIG = {
  student: {
    singular: "Student",
    plural: "Students",
    description: "Search, review and manage institution student master records.",
    identifier: "roll_number",
    identifierLabel: "Roll number",
    list: adminListStudentMaster,
    bulkStatus: adminBulkStudentStatus,
    exportData: adminExportStudentMaster,
    newHref: "/admin/students/new",
    sortOptions: [
      ["name", "Name"],
      ["roll_number", "Roll number"],
      ["email", "Email"],
      ["college", "College"],
      ["admission_year", "Admission year"],
      ["present_year", "Present year"],
      ["registration_status", "Registration status"],
      ["academic_status", "Academic status"],
      ["created_at", "Created date"],
    ],
  },
  faculty: {
    singular: "Faculty",
    plural: "Faculty",
    description: "Search, review and manage faculty masters and academic responsibilities.",
    identifier: "employee_code",
    identifierLabel: "Employee code",
    list: adminListFacultyMaster,
    bulkStatus: adminBulkFacultyStatus,
    exportData: adminExportFacultyMaster,
    newHref: "/admin/faculty/new",
    sortOptions: [
      ["name", "Name"],
      ["employee_code", "Employee code"],
      ["email", "Email"],
      ["college", "College"],
      ["department", "Department"],
      ["designation", "Designation"],
      ["registration_status", "Registration status"],
      ["employment_status", "Employment status"],
      ["created_at", "Created date"],
    ],
  },
};

function statusLabel(value) {
  return String(value || "Unavailable").replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

function contactLabel(record) {
  return record.email || "Email unavailable";
}

function ConfirmDialog({ open, title, message, busy, onCancel, onConfirm }) {
  const cancelRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    cancelRef.current?.focus();
    const close = (event) => {
      if (event.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [busy, onCancel, open]);
  if (!open) return null;
  return (
    <div className={styles.dialogLayer}>
      <div className={styles.confirmDialog} role="alertdialog" aria-modal="true" aria-labelledby="bulk-confirm-title" aria-describedby="bulk-confirm-message">
        <h2 id="bulk-confirm-title">{title}</h2>
        <p id="bulk-confirm-message">{message}</p>
        <div>
          <button ref={cancelRef} type="button" className={styles.secondaryButton} onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className={styles.primaryButton} onClick={onConfirm} disabled={busy}>{busy ? "Applying…" : "Confirm"}</button>
        </div>
      </div>
    </div>
  );
}

function SortHeader({ field, label, query, updateQuery }) {
  const active = query.sort === field;
  const ariaSort = active ? (query.order === "asc" ? "ascending" : "descending") : "none";
  return (
    <th scope="col" aria-sort={ariaSort}>
      <button type="button" onClick={() => updateQuery({ sort: field, order: active && query.order === "asc" ? "desc" : "asc", page: 1 })}>
        {label}<span aria-hidden="true">{active ? (query.order === "asc" ? " ↑" : " ↓") : ""}</span>
      </button>
    </th>
  );
}

function RecordDrawer({ kind, record, onClose, openerRef }) {
  const closeRef = useRef(null);
  function closeAndRestore() {
    onClose();
    window.requestAnimationFrame(() => openerRef.current?.focus());
  }
  useEffect(() => {
    if (!record) return undefined;
    closeRef.current?.focus();
    const close = (event) => {
      if (event.key === "Escape") closeAndRestore();
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [record]);
  if (!record) return null;
  const editHref = `/admin/${kind === "student" ? "students" : "faculty"}/${record.id}/edit`;
  const identifier = kind === "student" ? record.roll_number : record.employee_code;
  const fields = kind === "student"
    ? [
      ["Programme", record.programmes?.map((item) => item.title).join(", ") || "Unavailable"],
      ["College", record.college || "Unavailable"],
      ["Admission year", record.admission_year ?? "Unavailable"],
      ["Present year", record.present_year ?? "Unavailable"],
      ["Academic status", record.academic_status ? statusLabel(record.academic_status) : "Unavailable"],
    ]
    : [
      ["College", record.college || "Unavailable"],
      ["Department", record.department || "Unavailable"],
      ["Designation", record.designation || "Unavailable"],
      ["Employment status", record.employment_status ? statusLabel(record.employment_status) : "Unavailable"],
      ["Course coordinator assignments", record.coordinator_assignments],
      ["Subject expert assignments", record.subject_expert_assignments],
    ];
  return (
    <div className={styles.drawerLayer}>
      <button type="button" className={styles.drawerScrim} aria-label="Close record details" onClick={closeAndRestore} />
      <aside className={styles.recordDrawer} role="dialog" aria-modal="true" aria-labelledby="record-drawer-title">
        <div className={styles.drawerHeader}>
          <div><span>{kind === "student" ? "Student" : "Faculty"} master record</span><h2 id="record-drawer-title">{record.name}</h2></div>
          <button ref={closeRef} type="button" aria-label="Close record details" onClick={closeAndRestore}><XMarkIcon aria-hidden="true" /></button>
        </div>
        <div className={styles.drawerBody}>
          <dl>
            <div><dt>{kind === "student" ? "Roll number" : "Employee code"}</dt><dd>{identifier || "Unavailable"}</dd></div>
            <div><dt>Email</dt><dd>{record.email || "Unavailable"}</dd></div>
            <div><dt>Mobile</dt><dd>{record.mobile_masked || "Unavailable"}</dd></div>
            <div><dt>Registration</dt><dd>{statusLabel(record.registration_status)}</dd></div>
            <div><dt>Email verified</dt><dd>{record.email_verified ? "Verified" : "Not verified"}</dd></div>
            <div><dt>Mobile verified</dt><dd>{record.mobile_verified ? "Verified" : "Not verified"}</dd></div>
            {fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
            <div><dt>Last login</dt><dd>{record.last_login_available ? record.last_login_at : "Unavailable"}</dd></div>
          </dl>
        </div>
        <div className={styles.drawerActions}>
          <Link href={editHref}><PencilSquareIcon aria-hidden="true" /> Edit record</Link>
          <button type="button" className={styles.secondaryButton} onClick={closeAndRestore}>Close</button>
        </div>
      </aside>
    </div>
  );
}

export default function MasterWorkspace({ kind }) {
  const config = CONFIG[kind];
  const router = useRouter();
  const access = useAdminAccess();
  const query = useMemo(() => masterQueryFromRouter(router.query, kind), [kind, router.query]);
  const [searchInput, setSearchInput] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [records, setRecords] = useState({ status: "loading", items: [], total: 0, error: "" });
  const [summary, setSummary] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedIds, setSelectedIds] = useState([]);
  const [preview, setPreview] = useState(null);
  const previewOpenerRef = useRef(null);
  const [bulkAction, setBulkAction] = useState("deactivate");
  const [bulkTarget, setBulkTarget] = useState("");
  const [bulkResult, setBulkResult] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [auxiliary, setAuxiliary] = useState({ courses: [], subjects: [], available: true });

  useEffect(() => {
    if (router.isReady) setSearchInput(query.search);
  }, [query.search, router.isReady]);

  function updateQuery(patch, { replace = false } = {}) {
    const next = compactQuery({ ...query, ...patch });
    if (replace) router.replace({ pathname: router.pathname, query: next }, undefined, { shallow: true, scroll: false });
    else router.push({ pathname: router.pathname, query: next }, undefined, { shallow: true, scroll: false });
  }

  useEffect(() => {
    if (!router.isReady || searchInput === query.search) return undefined;
    const timeout = window.setTimeout(() => updateQuery({ search: searchInput, page: 1 }, { replace: true }), 350);
    return () => window.clearTimeout(timeout);
  }, [query.search, router.isReady, searchInput]);

  async function handleRequestError(error) {
    if (error?.response?.status === 401) {
      clearSession();
      await router.replace("/login?reason=expired");
      return true;
    }
    if (error?.response?.status === 403) {
      await router.replace("/login?reason=unauthorized");
      return true;
    }
    return false;
  }

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    let active = true;
    getAdminOperationsSummary({ signal: controller.signal })
      .then((response) => { if (active && response?.data && typeof response.data === "object") setSummary(response.data); })
      .catch((error) => { if (active && error?.code !== "ERR_CANCELED") handleRequestError(error); });
    return () => { active = false; controller.abort(); };
  }, [access.status]);

  useEffect(() => {
    if (access.status !== "ready") return undefined;
    const controller = new AbortController();
    let active = true;
    const requests = [getCourses(undefined, { signal: controller.signal })];
    if (kind === "faculty") requests.push(adminListSubjects({ signal: controller.signal }));
    Promise.all(requests)
      .then((responses) => {
        if (!active) return;
        const courses = Array.isArray(responses[0]?.data) ? responses[0].data : null;
        const subjects = kind === "faculty" && Array.isArray(responses[1]?.data) ? responses[1].data : kind === "student" ? [] : null;
        setAuxiliary({ courses: courses || [], subjects: subjects || [], available: courses !== null && subjects !== null });
      })
      .catch(async (error) => {
        if (!active || error?.code === "ERR_CANCELED") return;
        if (!(await handleRequestError(error))) setAuxiliary({ courses: [], subjects: [], available: false });
      });
    return () => { active = false; controller.abort(); };
  }, [access.status, kind]);

  useEffect(() => {
    if (access.status !== "ready" || !router.isReady) return undefined;
    const controller = new AbortController();
    let active = true;
    setRecords((current) => ({ ...current, status: "loading", error: "" }));
    config.list(compactQuery(query), { signal: controller.signal })
      .then((response) => {
        if (!active) return;
        if (!isMasterPageResponse(response?.data)) {
          setRecords({ status: "unavailable", items: [], total: 0, error: "The master-data service returned an invalid response." });
          return;
        }
        const hasFilters = Object.entries(query).some(([key, value]) => !["sort", "order", "page", "page_size"].includes(key) && value && value !== "all");
        setRecords({
          status: response.data.items.length ? "available" : hasFilters ? "no-results" : "empty",
          items: response.data.items,
          total: response.data.total,
          error: "",
        });
        setLastUpdated(new Date());
        setSelectedIds((ids) => ids.filter((id) => response.data.items.some((item) => item.id === id)));
      })
      .catch(async (error) => {
        if (!active || error?.code === "ERR_CANCELED") return;
        if (await handleRequestError(error)) return;
        setRecords({ status: "error", items: [], total: 0, error: getApiErrorMessage(error, `Unable to load ${config.plural.toLowerCase()}.`) });
      });
    return () => { active = false; controller.abort(); };
  }, [access.status, config, query, refreshKey, router.isReady]);

  if (access.status === "checking") return <BrandedState />;
  if (access.status === "error") return <BrandedState type="error" title="Administrator workspace unavailable" message={access.error} actionHref="/login" actionLabel="Return to login" />;

  const totalPages = Math.max(1, Math.ceil(records.total / query.page_size));
  const allPageSelected = records.items.length > 0 && records.items.every((record) => selectedIds.includes(record.id));
  const pageStart = records.total ? (query.page - 1) * query.page_size + 1 : 0;
  const pageEnd = Math.min(query.page * query.page_size, records.total);
  const activeFilterCount = Object.entries(query).filter(([key, value]) => !["status", "sort", "order", "page", "page_size", "search"].includes(key) && Boolean(value)).length;

  function togglePageSelection() {
    if (allPageSelected) setSelectedIds((ids) => ids.filter((id) => !records.items.some((record) => record.id === id)));
    else setSelectedIds((ids) => [...new Set([...ids, ...records.items.map((record) => record.id)])]);
  }

  async function applyBulk() {
    setBulkBusy(true);
    setBulkResult("");
    try {
      let response;
      if (kind === "faculty" && ["course_coordinator", "subject_expert"].includes(bulkAction)) {
        response = await adminBulkFacultyAssignment({ faculty_ids: selectedIds, assignment_type: bulkAction, target_id: Number(bulkTarget) });
      } else {
        response = await config.bulkStatus({ ids: selectedIds, action: bulkAction });
      }
      const result = response?.data;
      if (!result || !Number.isInteger(result.succeeded) || !Number.isInteger(result.failed)) throw new Error("Malformed bulk response");
      setBulkResult(`${result.succeeded} succeeded; ${result.failed} failed.${result.failed ? " Review individual records and try again." : ""}`);
      setSelectedIds([]);
      setConfirmOpen(false);
      setRefreshKey((value) => value + 1);
    } catch (error) {
      if (!(await handleRequestError(error))) setBulkResult(getApiErrorMessage(error, "Unable to apply the selected bulk action."));
      setConfirmOpen(false);
    } finally {
      setBulkBusy(false);
    }
  }

  async function exportCurrentView() {
    setExporting(true);
    setBulkResult("");
    try {
      const response = await config.exportData(compactQuery(query));
      const disposition = response.headers?.["content-disposition"] || "";
      const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `SYS_${kind}_master.csv`;
      downloadBlob(response.data, filename);
    } catch (error) {
      if (!(await handleRequestError(error))) setBulkResult(getApiErrorMessage(error, "Unable to export the current view."));
    } finally {
      setExporting(false);
    }
  }

  const assignmentNeedsTarget = kind === "faculty" && ["course_coordinator", "subject_expert"].includes(bulkAction);
  const targetOptions = bulkAction === "course_coordinator" ? auxiliary.courses : auxiliary.subjects;
  const canConfirmBulk = selectedIds.length > 0 && (!assignmentNeedsTarget || Boolean(bulkTarget));
  const confirmLabel = bulkAction.replaceAll("_", " ");

  return (
    <>
      <Head><title>{config.singular} Master | SYS</title><meta name="description" content={`SYS ${config.singular.toLowerCase()} master management workspace.`} /><link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" /></Head>
      <AdminShell user={access.user} unreadNotifications={summary?.unread_notifications || 0} pageTitle={`${config.singular} Master`} breadcrumb="People & Access" scopeLabel={summary?.scope_label}>
        <div className={styles.workspaceContent}>
          <section className={styles.pageHeading}>
            <div><span>People & Access</span><h1>{config.singular} Master</h1><p>{config.description}</p></div>
            <div className={styles.headingActions}>
              <button type="button" className={styles.secondaryButton} onClick={() => setRefreshKey((value) => value + 1)} disabled={records.status === "loading"}><ArrowPathIcon aria-hidden="true" /> Refresh</button>
              <button type="button" className={styles.secondaryButton} onClick={exportCurrentView} disabled={exporting}><ArrowDownTrayIcon aria-hidden="true" /> {exporting ? "Exporting…" : "Export current view"}</button>
              <Link href={config.newHref} className={styles.primaryButton}><PlusIcon aria-hidden="true" /> Add individual</Link>
            </div>
          </section>

          <div className={styles.updatedRow}><span>{lastUpdated ? `Last updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Not updated yet"}</span></div>

          <section className={styles.controlsCard} aria-label={`${config.singular} master controls`}>
            <div className={styles.searchRow}>
              <form onSubmit={(event) => { event.preventDefault(); updateQuery({ search: searchInput, page: 1 }); }} role="search">
                <MagnifyingGlassIcon aria-hidden="true" />
                <label className="sr-only" htmlFor={`${kind}-master-search`}>Search {config.plural.toLowerCase()}</label>
                <input id={`${kind}-master-search`} value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={`Search by ${config.identifierLabel.toLowerCase()}, name, email or mobile`} />
                {searchInput && <button type="button" aria-label="Clear search" onClick={() => { setSearchInput(""); updateQuery({ search: "", page: 1 }); }}><XMarkIcon aria-hidden="true" /></button>}
              </form>
              <button type="button" className={styles.filterToggle} aria-expanded={filtersOpen} aria-controls={`${kind}-master-filters`} onClick={() => setFiltersOpen((value) => !value)}>
                <AdjustmentsHorizontalIcon aria-hidden="true" /> Filters {activeFilterCount > 0 && <span>{activeFilterCount}</span>}
              </button>
            </div>

            <div className={styles.statusTabs} role="tablist" aria-label="Master record status">
              {MASTER_STATUS_TABS.map((tab) => <button key={tab.value} type="button" role="tab" aria-selected={query.status === tab.value} onClick={() => updateQuery({ status: tab.value, page: 1 })}>{tab.label}</button>)}
            </div>

            <div id={`${kind}-master-filters`} className={styles.filterPanel} hidden={!filtersOpen}>
              <label>College<input value={query.college} onChange={(event) => updateQuery({ college: event.target.value, page: 1 }, { replace: true })} /></label>
              <label>Registration<select value={query.registration_status} onChange={(event) => updateQuery({ registration_status: event.target.value, page: 1 })}><option value="">All</option><option value="PENDING_ACTIVATION">Pending activation</option><option value="ACTIVE">Active</option><option value="DISABLED">Disabled</option></select></label>
              {kind === "student" ? (
                <>
                  <label>Programme<select value={query.programme_id} onChange={(event) => updateQuery({ programme_id: event.target.value, page: 1 })}><option value="">All</option>{auxiliary.courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
                  <label>Admission year<input inputMode="numeric" value={query.admission_year} onChange={(event) => updateQuery({ admission_year: event.target.value, page: 1 }, { replace: true })} /></label>
                  <label>Present year<input inputMode="numeric" value={query.present_year} onChange={(event) => updateQuery({ present_year: event.target.value, page: 1 }, { replace: true })} /></label>
                  <label>Academic status<select value={query.academic_status} onChange={(event) => updateQuery({ academic_status: event.target.value, page: 1 })}><option value="">All</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label>
                </>
              ) : (
                <>
                  <label>Department<input value={query.department} onChange={(event) => updateQuery({ department: event.target.value, page: 1 }, { replace: true })} /></label>
                  <label>Designation<input value={query.designation} onChange={(event) => updateQuery({ designation: event.target.value, page: 1 }, { replace: true })} /></label>
                  <label>Employment status<select value={query.employment_status} onChange={(event) => updateQuery({ employment_status: event.target.value, page: 1 })}><option value="">All</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label>
                  <label>Responsibility<select value={query.responsibility} onChange={(event) => updateQuery({ responsibility: event.target.value, page: 1 })}><option value="">All</option><option value="course_coordinator">Course coordinator</option><option value="subject_expert">Subject expert</option><option value="unassigned">Unassigned</option></select></label>
                </>
              )}
              <label>Sort by<select value={query.sort} onChange={(event) => updateQuery({ sort: event.target.value, page: 1 })}>{config.sortOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label>Order<select value={query.order} onChange={(event) => updateQuery({ order: event.target.value, page: 1 })}><option value="asc">Ascending</option><option value="desc">Descending</option></select></label>
              <button type="button" className={styles.resetButton} onClick={() => router.push({ pathname: router.pathname, query: {} }, undefined, { shallow: true })}>Reset filters</button>
              {!auxiliary.available && <p role="status">Programme or subject filters are unavailable.</p>}
            </div>
          </section>

          {selectedIds.length > 0 && (
            <section className={styles.bulkBar} aria-label="Bulk actions">
              <strong>{selectedIds.length} selected</strong>
              <label>Action<select value={bulkAction} onChange={(event) => { setBulkAction(event.target.value); setBulkTarget(""); }}><option value="activate">Activate</option><option value="deactivate">Deactivate</option>{kind === "faculty" && <><option value="course_coordinator">Assign course coordinator</option><option value="subject_expert">Assign subject expert</option></>}</select></label>
              {assignmentNeedsTarget && <label>Assign to<select value={bulkTarget} onChange={(event) => setBulkTarget(event.target.value)}><option value="">Select {bulkAction === "course_coordinator" ? "programme" : "subject"}</option>{targetOptions.map((item) => <option key={item.id} value={item.id}>{item.title || item.name}</option>)}</select></label>}
              <button type="button" className={styles.primaryButton} disabled={!canConfirmBulk} onClick={() => setConfirmOpen(true)}>Apply</button>
              <button type="button" className={styles.secondaryButton} onClick={() => setSelectedIds([])}>Clear</button>
            </section>
          )}
          {bulkResult && <p className={styles.resultBanner} role="status">{bulkResult}</p>}

          <section className={styles.tableCard} aria-labelledby={`${kind}-records-title`}>
            <div className={styles.tableHeading}><div><h2 id={`${kind}-records-title`}>{config.plural}</h2><span>{records.total} matching records</span></div><label>Rows per page<select value={query.page_size} onChange={(event) => updateQuery({ page_size: Number(event.target.value), page: 1 })}>{MASTER_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}</select></label></div>

            {records.status === "loading" && <div className={styles.inlineState}><span aria-hidden="true" /><h2>Loading {config.plural.toLowerCase()}</h2><p>Applying the current server-side search and filters.</p></div>}
            {records.status === "unavailable" && <BrandedState type="error" compact title="Data unavailable" message={records.error} />}
            {records.status === "error" && <BrandedState type="error" compact title={`Unable to load ${config.plural.toLowerCase()}`} message={records.error} />}
            {records.status === "empty" && <BrandedState compact title={`No ${config.plural.toLowerCase()} yet`} message={`Add the first ${config.singular.toLowerCase()} master record when institution data is ready.`} actionHref={config.newHref} actionLabel="Add individual" />}
            {records.status === "no-results" && <BrandedState compact title="No matching records" message="Adjust or reset the current search and filters." />}

            {records.status === "available" && (
              <>
                <div className={styles.tableWrap}>
                  <table>
                    <thead><tr><th className={styles.selectColumn}><input type="checkbox" aria-label="Select all records on this page" checked={allPageSelected} onChange={togglePageSelection} /></th><SortHeader field={config.identifier} label={config.identifierLabel} query={query} updateQuery={updateQuery} /><SortHeader field="name" label="Name & contact" query={query} updateQuery={updateQuery} />{kind === "student" ? <><th scope="col">Programme</th><SortHeader field="college" label="College & year" query={query} updateQuery={updateQuery} /></> : <><SortHeader field="department" label="Department" query={query} updateQuery={updateQuery} /><th scope="col">Responsibilities</th></>}<SortHeader field="registration_status" label="Status" query={query} updateQuery={updateQuery} /><th scope="col">Actions</th></tr></thead>
                    <tbody>{records.items.map((record) => (
                      <tr key={record.id}>
                        <td><input type="checkbox" aria-label={`Select ${record.name}`} checked={selectedIds.includes(record.id)} onChange={() => setSelectedIds((ids) => ids.includes(record.id) ? ids.filter((id) => id !== record.id) : [...ids, record.id])} /></td>
                        <td><strong>{record[config.identifier] || "Unavailable"}</strong></td>
                        <td><strong>{record.name}</strong><span>{contactLabel(record)}</span><span>{record.mobile_masked || "Mobile unavailable"}</span></td>
                        {kind === "student" ? <><td>{record.programmes?.map((item) => item.title).join(", ") || "Unavailable"}</td><td>{record.college || "Unavailable"}<span>{record.admission_year ? `Admitted ${record.admission_year}` : "Admission year unavailable"}</span></td></> : <><td>{record.department || "Unavailable"}<span>{record.designation || "Designation unavailable"}</span></td><td>{record.coordinator_assignments} coordinator · {record.subject_expert_assignments} expert</td></>}
                        <td><span className={`${styles.statusBadge} ${record.is_active ? styles.statusActive : styles.statusInactive}`}>{statusLabel(record.registration_status)}</span><small>{kind === "student" ? statusLabel(record.academic_status) : statusLabel(record.employment_status)}</small></td>
                        <td><div className={styles.rowActions}><button type="button" ref={selectedIds[0] === record.id ? previewOpenerRef : undefined} onClick={(event) => { previewOpenerRef.current = event.currentTarget; setPreview(record); }}><EyeIcon aria-hidden="true" /> View</button><Link href={`/admin/${kind === "student" ? "students" : "faculty"}/${record.id}/edit`}><PencilSquareIcon aria-hidden="true" /> Edit</Link></div></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>

                <div className={styles.mobileCards}>{records.items.map((record) => (
                  <article key={record.id}><div><input type="checkbox" aria-label={`Select ${record.name}`} checked={selectedIds.includes(record.id)} onChange={() => setSelectedIds((ids) => ids.includes(record.id) ? ids.filter((id) => id !== record.id) : [...ids, record.id])} /><span className={`${styles.statusBadge} ${record.is_active ? styles.statusActive : styles.statusInactive}`}>{statusLabel(record.registration_status)}</span></div><h3>{record.name}</h3><strong>{record[config.identifier] || "Identifier unavailable"}</strong><p>{contactLabel(record)}<br />{record.mobile_masked || "Mobile unavailable"}</p><dl><div><dt>{kind === "student" ? "Programme" : "Department"}</dt><dd>{kind === "student" ? record.programmes?.map((item) => item.title).join(", ") || "Unavailable" : record.department || "Unavailable"}</dd></div><div><dt>College</dt><dd>{record.college || "Unavailable"}</dd></div></dl><div className={styles.rowActions}><button type="button" onClick={(event) => { previewOpenerRef.current = event.currentTarget; setPreview(record); }}><EyeIcon aria-hidden="true" /> View</button><Link href={`/admin/${kind === "student" ? "students" : "faculty"}/${record.id}/edit`}><PencilSquareIcon aria-hidden="true" /> Edit</Link></div></article>
                ))}</div>

                <nav className={styles.pagination} aria-label={`${config.singular} master pagination`}><span>Showing {pageStart}–{pageEnd} of {records.total}</span><div><button type="button" aria-label="Previous page" disabled={query.page <= 1} onClick={() => updateQuery({ page: query.page - 1 })}><ChevronLeftIcon aria-hidden="true" /></button><span>Page {query.page} of {totalPages}</span><button type="button" aria-label="Next page" disabled={query.page >= totalPages} onClick={() => updateQuery({ page: query.page + 1 })}><ChevronRightIcon aria-hidden="true" /></button></div></nav>
              </>
            )}
          </section>
        </div>
      </AdminShell>

      <RecordDrawer kind={kind} record={preview} onClose={() => setPreview(null)} openerRef={previewOpenerRef} />
      <ConfirmDialog open={confirmOpen} title={`Confirm bulk ${confirmLabel}`} message={`Apply “${confirmLabel}” to ${selectedIds.length} selected ${selectedIds.length === 1 ? "record" : "records"}? Successful changes will be audited.`} busy={bulkBusy} onCancel={() => setConfirmOpen(false)} onConfirm={applyBulk} />
    </>
  );
}
