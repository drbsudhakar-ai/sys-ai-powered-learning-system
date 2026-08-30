import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import API, { getMe, getApiErrorMessage } from "../../src/api";
import { downloadBlob } from "../../src/adminMaster";
import { courseHomeLink } from "../../src/workspaceNavigation";
import { SYLLABUS_PAGES, syllabusPagePath } from "../../src/syllabusPages";
import { reorder, diffNodes } from "../../src/syllabusReview";
import ApprovedSyllabusDownload from "./ApprovedSyllabusDownload";
import styles from "./SyllabusReview.module.css";
import WorkspaceBreadcrumbs from "../auth/WorkspaceBreadcrumbs";

const labels = {
  NOT_REQUESTED: "Review not requested",
  IN_REVIEW: "Under expert review",
  RETURNED: "Changes requested",
  RECOMMENDED: "Final approval pending",
  APPROVED: "Finally approved",
  CANCELLED: "Request cancelled",
};
export default function SubjectReviewDashboard() {
  const router = useRouter(),
    id = router.query.id;
  const [data, setData] = useState(null),
    [role, setRole] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false),
    [selected, setSelected] = useState(null),
    [nodes, setNodes] = useState([]),
    [comment, setComment] = useState(""),
    [decision, setDecision] = useState(""),
    [dirty, setDirty] = useState(false);
  const [reviewId, setReviewId] = useState(null),
    [assignments, setAssignments] = useState({}),
    [changingExpert, setChangingExpert] = useState(null);
  const root = `/courses/${id}/syllabus-review`;
  const expertMode = router.query.mode === "expert";
  const review =
    data?.reviews.find(
      (r) => r.id === Number(reviewId || router.query.review),
    ) || data?.reviews[0];
  const task = review?.tasks.find(
    (t) => t.id === Number(selected || router.query.subject),
  );
  const finalApprovalModal = Boolean(
    task &&
    !expertMode &&
    task.status === "RECOMMENDED" &&
    (role === "admin" || data?.can_manage),
  );
  const visibleSubjects =
    expertMode && task
      ? review.subjects.filter((s) => s.key === task.subject_key)
      : review?.subjects || [];
  async function refresh() {
    const res = await API.get(`${root}/subject-dashboard`);
    setData(res.data);
    return res.data;
  }
  useEffect(() => {
    if (!router.isReady || !id) return;
    let active = true;
    Promise.all([API.get(`${root}/subject-dashboard`), getMe()])
      .then(([res, me]) => {
        if (active) {
          setData(res.data);
          setRole(me.data.role);
        }
      })
      .catch((e) => {
        if (active) setError(getApiErrorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [router.isReady, id]);
  useEffect(() => {
    const warn = (e) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    if (!finalApprovalModal) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event) => {
      if (event.key === "Escape" && !busy) {
        setSelected(null);
        setDecision("");
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [finalApprovalModal, busy]);
  useEffect(() => {
    if (!review || !router.query.subject || selected) return;
    const t = review.tasks.find((x) => x.id === Number(router.query.subject));
    if (t) open(t);
  }, [review?.id, router.query.subject, data]);
  function leave(e) {
    if (
      busy ||
      (dirty && !window.confirm("Discard unsaved subject recommendations?"))
    )
      e.preventDefault();
  }
  function open(t) {
    if (dirty && !window.confirm("Discard unsaved subject recommendations?"))
      return;
    setSelected(t.id);
    setNodes(t.proposed_nodes || []);
    setComment(t.comment || "");
    setDecision("");
    setDirty(false);
  }
  async function act(subjectKey, action, version, extra = {}) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await API.post(`${root}/reviews/${review.id}/subject-action`, {
        subject_key: subjectKey,
        action,
        version,
        ...extra,
      });
      setDirty(false);
      setChangingExpert(null);
      setAssignments({});
      const updated = await refresh();
      const fresh = updated.reviews
        .find((r) => r.id === review.id)
        ?.tasks.find((t) => t.subject_key === subjectKey);
      if (action === "assign" || action === "unassign") {
        setSelected(null);
      } else if (fresh) {
        setSelected(fresh.id);
        setNodes(fresh.proposed_nodes || []);
        setComment(fresh.comment || "");
        setDecision("");
      }
      setMessage(
        action === "request"
          ? "Review request sent to the assigned subject expert."
          : action === "approve"
            ? "Subject syllabus finally approved."
            : action === "recommend"
              ? "Recommendation submitted for final approval."
              : action === "assign"
                ? "Subject expert assigned. You can now request review."
                : "Subject review saved.",
      );
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function pdf(subjectKey) {
    setBusy(true);
    setError("");
    try {
      const res = await API.get(`${root}/reviews/${review.id}/syllabus.pdf`, {
        params: { subject_key: subjectKey },
        responseType: "blob",
      });
      downloadBlob(
        res.data,
        `SYS_${subjectKey ? "Subject" : "Complete"}_Syllabus_${id}_v${review.version}.pdf`,
      );
    } catch (e) {
      let msg = "Unable to download syllabus.";
      try {
        msg = JSON.parse(await e.response.data.text()).detail;
      } catch {}
      setError(typeof msg === "string" ? msg : "Unable to download syllabus.");
    } finally {
      setBusy(false);
    }
  }
  function edit(key, field, value) {
    setNodes((old) =>
      old.map((n) => (n.key === key ? { ...n, [field]: value } : n)),
    );
    setDirty(true);
  }
  function add(level, parent) {
    const siblings = nodes.filter((n) => n.parent === parent);
    setNodes([
      ...nodes,
      {
        key: `new:${crypto.randomUUID()}`,
        level,
        parent,
        name: "",
        description: "",
        learning_outcome: "",
        sequence: Math.max(0, ...siblings.map((n) => n.sequence)) + 1,
      },
    ]);
    setDirty(true);
  }
  const mayEdit =
    task &&
    task.reviewer_id === data?.actor_id &&
    ["IN_REVIEW", "RETURNED"].includes(task.status) &&
    !data?.archived;
  function tree(parent = null) {
    return nodes
      .filter((n) => n.parent === parent)
      .sort((a, b) => a.sequence - b.sequence)
      .map((n) => (
        <details
          className={styles.node}
          key={n.key}
          open={n.level === "subject"}
        >
          <summary>
            {n.level} · {n.sequence}. {n.name || "New item"}
          </summary>
          {mayEdit && ["topic", "subtopic"].includes(n.level) ? (
            <>
              <label>
                Name
                <input
                  maxLength={200}
                  value={n.name}
                  onChange={(e) => edit(n.key, "name", e.target.value)}
                  disabled={busy}
                />
              </label>
              <label>
                Description
                <textarea
                  maxLength={500}
                  value={n.description}
                  onChange={(e) => edit(n.key, "description", e.target.value)}
                  disabled={busy}
                />
              </label>
              <div className={styles.actions}>
                {[-1, 1].map((d) => (
                  <button
                    key={d}
                    disabled={busy}
                    onClick={() => {
                      setNodes(reorder(nodes, n.key, d));
                      setDirty(true);
                    }}
                  >
                    Move {d === -1 ? "up" : "down"}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p>{n.description || "No description recorded."}</p>
          )}
          {n.learning_outcome && <p>Learning outcome: {n.learning_outcome}</p>}
          {mayEdit && ["unit", "topic"].includes(n.level) && (
            <button
              disabled={busy}
              onClick={() =>
                add(n.level === "unit" ? "topic" : "subtopic", n.key)
              }
            >
              Add {n.level === "unit" ? "topic" : "subtopic"}
            </button>
          )}
          {tree(n.key)}
        </details>
      ));
  }
  return (
    <main className={styles.workspace}>
      <Head>
        <title>
          {expertMode ? "Subject Expert Review" : "Subject Reviews & Approvals"}{" "}
          | SYS
        </title>
      </Head>
      {role === "faculty" ? (
        <WorkspaceBreadcrumbs
          items={[
            { label: "Faculty Workspace", href: "/faculty-dashboard" },
            { label: "Assigned Courses" },
            {
              label: expertMode
                ? "Subject Expert Courses"
                : "Coordinator Courses",
              href: expertMode
                ? "/faculty/subject-expert-courses"
                : "/faculty/coordinator-courses",
            },
            {
              label: expertMode
                ? "Subject Expert Review"
                : "Reviews & Approvals",
            },
          ]}
        />
      ) : role ? (
        <Link
          className={styles.back}
          href={courseHomeLink(role, id).href}
          onClick={leave}
        >
          ← {courseHomeLink(role, id).label}
        </Link>
      ) : null}
      <header className={styles.hero}>
        <span>SYS · Academic governance</span>
        <h1>{expertMode ? "Subject Expert Review" : "Reviews & Approvals"}</h1>
        <p>{data?.course_title || "Loading course…"}</p>
        <p>
          {expertMode
            ? "Review only the subject assigned to you and submit your academic recommendation."
            : "Strengthen Your Skills · Shape Your Successful Future"}
        </p>
      </header>
      {data && !expertMode && (
        <nav className={styles.pageNav}>
          {SYLLABUS_PAGES.filter(
            ([p]) => data.can_manage || p === "reviews",
          ).map(([p, label]) => (
            <Link
              key={p}
              href={syllabusPagePath(role, id, p, review?.id)}
              aria-current={p === "reviews" ? "page" : undefined}
              onClick={leave}
            >
              {label}
            </Link>
          ))}
        </nav>
      )}
      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className={styles.success} role="status">
          {message}
        </div>
      )}
      {!data ? (
        <p>Loading academic permissions…</p>
      ) : !review ? (
        <section className={styles.panel}>
          <h2>Prepare the syllabus first</h2>
          <p>
            Save the syllabus in Syllabus Structure or Excel Upload, then assign
            experts and request review.
          </p>
        </section>
      ) : (
        <>
          {data.reviews.length > 1 && (
            <label>
              Saved syllabus version
              <select
                disabled={dirty || busy}
                value={review.id}
                onChange={(e) => {
                  setReviewId(e.target.value);
                  setSelected(null);
                }}
              >
                {data.reviews.map((r) => (
                  <option key={r.id} value={r.id}>
                    Syllabus {r.id} · {r.status.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
          )}
          <section className={styles.panel}>
            <h2>
              {expertMode
                ? "My assigned subject review"
                : "Subject approval readiness"}
            </h2>
            <p>
              {expertMode
                ? "Subject-expert recommendation is separate from coordinator final approval."
                : `${review.subjects.length} subjects · ${review.tasks.filter((t) => t.status === "APPROVED").length} finally approved · ${review.tasks.filter((t) => t.status === "RECOMMENDED").length} awaiting final approval`}
            </p>
            <p>
              {expertMode
                ? "Review the assigned syllabus branch and record your recommendation below."
                : "Expert recommendation and final approval are separate. Publication remains an explicit course action."}
            </p>
            {data.can_manage && !expertMode && (
              <button
                disabled={busy || dirty || !review.subjects.length}
                onClick={() => pdf()}
              >
                Download complete syllabus PDF
              </button>
            )}
            {dirty && (
              <p>Save your changes before downloading or changing subjects.</p>
            )}
            <div className={styles.previewTable}>
              <table>
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Assigned subject expert</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleSubjects.map((s) => {
                    const t = review.tasks.find((t) => t.subject_key === s.key);
                    const existing = data.faculty.filter((f) =>
                      s.eligible_reviewers?.includes(f.id),
                    );
                    return (
                      <tr key={s.key}>
                        <td>{s.name}</td>
                        <td>
                          {t?.reviewer_name ||
                            existing.map((f) => f.name).join(", ") ||
                            "Not assigned"}
                          {t?.reviewer_id && !t.assignment_valid && (
                            <p>
                              Review unavailable: check faculty registration,
                              active status and academic responsibility.
                            </p>
                          )}
                          {data.can_manage &&
                            !expertMode &&
                            review.status !== "APPROVED" &&
                            (!t ||
                              ["NOT_REQUESTED", "CANCELLED"].includes(
                                t.status,
                              )) && (
                              <>
                                {(t?.reviewer_id || existing.length > 0) &&
                                changingExpert !== s.key ? (
                                  <button
                                    disabled={busy || dirty || data.archived}
                                    onClick={() => {
                                      setChangingExpert(s.key);
                                      setAssignments({
                                        ...assignments,
                                        [s.key]: String(
                                          t?.reviewer_id ||
                                            existing[0]?.id ||
                                            "",
                                        ),
                                      });
                                    }}
                                  >
                                    Change expert
                                  </button>
                                ) : (
                                  <>
                                    <label>
                                      Subject expert
                                      <select
                                        disabled={
                                          busy || dirty || data.archived
                                        }
                                        value={assignments[s.key] || ""}
                                        onChange={(e) =>
                                          setAssignments({
                                            ...assignments,
                                            [s.key]: e.target.value,
                                          })
                                        }
                                      >
                                        <option value="">Select faculty</option>
                                        {data.faculty.map((f) => (
                                          <option key={f.id} value={f.id}>
                                            {f.name}
                                            {f.employee_code
                                              ? ` · ${f.employee_code}`
                                              : ""}
                                            {f.department
                                              ? ` · ${f.department}`
                                              : ""}
                                            {f.account_status !== "ACTIVE"
                                              ? " · Registration pending"
                                              : ""}
                                          </option>
                                        ))}
                                      </select>
                                    </label>
                                    <button
                                      disabled={
                                        !assignments[s.key] ||
                                        busy ||
                                        dirty ||
                                        data.archived
                                      }
                                      onClick={() =>
                                        act(s.key, "assign", review.version, {
                                          reviewer_id: Number(
                                            assignments[s.key],
                                          ),
                                        })
                                      }
                                    >
                                      {t?.reviewer_id || existing.length
                                        ? "Save expert change"
                                        : "Assign subject expert"}
                                    </button>
                                    {t?.reviewer_id && (
                                      <button
                                        disabled={busy}
                                        onClick={() => setChangingExpert(null)}
                                      >
                                        Cancel
                                      </button>
                                    )}
                                    <p>
                                      Faculty master records are listed here.
                                      Review requests require an active
                                      registered account.
                                    </p>
                                    {!data.faculty.length && (
                                      <p>
                                        No eligible faculty. Check Faculty
                                        Master.
                                      </p>
                                    )}
                                  </>
                                )}
                              </>
                            )}
                        </td>
                        <td>
                          {labels[t?.status] ||
                            (existing.length
                              ? "Review not requested"
                              : "Expert assignment required")}
                        </td>
                        <td>
                          <div className={styles.actions}>
                            {(expertMode || !data.can_manage) &&
                              t?.source_nodes?.length > 0 && (
                                <button
                                  disabled={busy || dirty}
                                  onClick={() => open(t)}
                                >
                                  Open subject review
                                </button>
                              )}
                            {data.can_manage &&
                              !expertMode &&
                              t?.status === "RECOMMENDED" && (
                                <button
                                  disabled={busy || dirty}
                                  onClick={() => open(t)}
                                >
                                  Open expert recommendation
                                </button>
                              )}
                            <button
                              disabled={busy || dirty}
                              onClick={() => pdf(s.key)}
                            >
                              Download subject PDF
                            </button>
                            {data.can_manage &&
                              !expertMode &&
                              ((t?.reviewer_id &&
                                ["NOT_REQUESTED", "CANCELLED"].includes(
                                  t.status,
                                )) ||
                                (!t?.reviewer_id &&
                                  existing.filter(
                                    (f) => f.account_status === "ACTIVE",
                                  ).length === 1)) && (
                                <button
                                  disabled={
                                    busy ||
                                    dirty ||
                                    data.archived ||
                                    (t?.reviewer_id && !t.assignment_valid)
                                  }
                                  onClick={() =>
                                    act(s.key, "request", review.version)
                                  }
                                >
                                  Request review
                                </button>
                              )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
          {task &&
            (expertMode ||
              !data.can_manage ||
              task.status === "RECOMMENDED") && (
              <div
                className={
                  finalApprovalModal ? styles.approvalBackdrop : undefined
                }
                role={finalApprovalModal ? "dialog" : undefined}
                aria-modal={finalApprovalModal ? "true" : undefined}
                aria-labelledby={
                  finalApprovalModal ? "final-approval-title" : undefined
                }
                onMouseDown={(event) => {
                  if (
                    finalApprovalModal &&
                    event.target === event.currentTarget &&
                    !busy
                  ) {
                    setSelected(null);
                    setDecision("");
                  }
                }}
              >
                <section className={styles.panel}>
                  {finalApprovalModal && (
                    <div className={styles.approvalModalHeader}>
                      <div>
                        <span>SUBJECT EXPERT RECOMMENDATION</span>
                        <h2 id="final-approval-title">
                          Review and final decision
                        </h2>
                      </div>
                      <button
                        type="button"
                        className={styles.modalClose}
                        aria-label="Close expert recommendation"
                        disabled={busy}
                        onClick={() => {
                          setSelected(null);
                          setDecision("");
                        }}
                      >
                        <XMarkIcon aria-hidden="true" />
                      </button>
                    </div>
                  )}
                  <h2>
                    {
                      review.subjects.find((s) => s.key === task.subject_key)
                        ?.name
                    }
                  </h2>
                  <p>{labels[task.status]}</p>
                  {task.decision_comment && (
                    <div className={styles.notice}>
                      Coordinator feedback: {task.decision_comment}
                    </div>
                  )}
                  {(expertMode || !data.can_manage) && tree()}
                  {mayEdit && (
                    <>
                      <label>
                        Academic recommendation / proposed changes
                        <textarea
                          maxLength={2000}
                          value={comment}
                          disabled={busy}
                          onChange={(e) => {
                            setComment(e.target.value);
                            setDirty(true);
                          }}
                        />
                      </label>
                      <div className={styles.actions}>
                        <button
                          disabled={busy}
                          onClick={() =>
                            act(task.subject_key, "save", task.version, {
                              nodes,
                              comment,
                            })
                          }
                        >
                          Save recommendations
                        </button>
                        <button
                          className={styles.primary}
                          disabled={
                            busy ||
                            !comment.trim() ||
                            nodes.some((n) => !n.name.trim())
                          }
                          onClick={() =>
                            act(task.subject_key, "recommend", task.version, {
                              nodes,
                              comment,
                            })
                          }
                        >
                          {diffNodes(task.source_nodes, nodes).length
                            ? "Submit proposed changes"
                            : "Recommend approval without changes"}
                        </button>
                      </div>
                    </>
                  )}
                  {data.can_manage &&
                    !expertMode &&
                    task.status === "RECOMMENDED" && (
                      <>
                        <h3>Change comparison</h3>
                        {diffNodes(task.source_nodes, task.proposed_nodes)
                          .length ? (
                          diffNodes(task.source_nodes, task.proposed_nodes).map(
                            (c) => (
                              <article
                                key={c.after.key}
                                className={styles.change}
                              >
                                <strong>
                                  {c.kind}: {c.after.name}
                                </strong>
                                <div className={styles.compare}>
                                  <div>
                                    <b>Before</b>
                                    <p>
                                      {c.before?.name || "New item"} ·{" "}
                                      {c.before?.description}
                                    </p>
                                    <p>Order: {c.before?.sequence || "—"}</p>
                                  </div>
                                  <div>
                                    <b>Proposed</b>
                                    <p>
                                      {c.after.name} · {c.after.description}
                                    </p>
                                    <p>Order: {c.after.sequence}</p>
                                  </div>
                                </div>
                              </article>
                            ),
                          )
                        ) : (
                          <p>Expert recommends approval without changes.</p>
                        )}
                        <p>Expert recommendation: {task.comment}</p>
                        <label>
                          Final decision / feedback
                          <textarea
                            maxLength={2000}
                            value={decision}
                            onChange={(e) => setDecision(e.target.value)}
                            disabled={busy}
                          />
                        </label>
                        <div className={styles.actions}>
                          <button
                            className={styles.primary}
                            disabled={
                              busy ||
                              !decision.trim() ||
                              data.archived ||
                              task.reviewer_id === data.actor_id
                            }
                            onClick={() => {
                              if (
                                window.confirm(
                                  "Finally approve this subject syllabus?",
                                )
                              )
                                act(task.subject_key, "approve", task.version, {
                                  comment: decision,
                                });
                            }}
                          >
                            Finally approve subject
                          </button>
                          <button
                            disabled={busy || !decision.trim() || data.archived}
                            onClick={() =>
                              act(task.subject_key, "return", task.version, {
                                comment: decision,
                              })
                            }
                          >
                            Return for changes
                          </button>
                        </div>
                        {task.reviewer_id === data.actor_id && (
                          <p>
                            A different administrator or coordinator must grant
                            final approval.
                          </p>
                        )}
                      </>
                    )}
                </section>
              </div>
            )}
          {data.can_manage && !expertMode && (
            <section className={styles.panel}>
              <details>
                <summary>Approved version history and downloads</summary>
                {data.revisions.length ? (
                  data.revisions.map((v) => (
                    <div className={styles.version} key={v.number}>
                      <span>
                        Revision {v.number} ·{" "}
                        {v.published_at
                          ? "Approved and published"
                          : "Approved - not yet published"}
                      </span>
                      <ApprovedSyllabusDownload
                        courseId={id}
                        revision={v.number}
                      />
                    </div>
                  ))
                ) : (
                  <p>No fully approved version yet.</p>
                )}
              </details>
              <details>
                <summary>Review audit history</summary>
                {review.history.map((h, i) => (
                  <p key={i}>
                    {h.action.replace("syllabus.", "").replaceAll("_", " ")} ·{" "}
                    {new Date(h.at).toLocaleString()} ·{" "}
                    {h.details?.comment || h.details?.reason || ""}
                  </p>
                ))}
              </details>
            </section>
          )}
        </>
      )}
    </main>
  );
}
