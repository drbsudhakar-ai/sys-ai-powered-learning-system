import { useEffect, useState } from "react";
import { getLectureRoster, inviteLectureLearner, getApiErrorMessage } from "../../src/api";

export default function ClassroomRoster({ sessionId }) {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [closed, setClosed] = useState(false);
  const [ready, setReady] = useState(false);
  async function load() {
    const { data } = await getLectureRoster(sessionId);
    setRows(data.items); setClosed(["COMPLETED", "CANCELLED", "ARCHIVED"].includes(data.session_status)); setReady(true);
  }
  useEffect(() => { setReady(false); load().catch((e) => setError(getApiErrorMessage(e))); }, [sessionId]);
  async function invite() {
    setBusy(true); setError(""); setNotice("");
    let added = 0; const failed = [];
    for (const userId of selected) {
      try { await inviteLectureLearner(sessionId, userId); added++; }
      catch (e) { failed.push(userId); if (e.response?.status === 401 || e.response?.status === 403) { setError("Permission changed. Reload the classroom before continuing."); break; } }
    }
    setNotice(`${added} learners invited. ${failed.length ? "Some invitations did not complete; refresh and retry the remaining selections." : "Inviting does not mark attendance or learning completion."}`);
    setSelected(failed);
    try { await load(); } catch (e) { setError(getApiErrorMessage(e)); }
    setBusy(false);
  }
  return <details className="classroom-roster"><summary>Faculty classroom roster · {rows.filter((row) => row.participant_id).length} invited</summary>
    <p>Select actively enrolled learners for this common/hybrid session. Students enter from their Learning Sessions page. Projector viewers still need their own participation evidence; attendance is not automatic completion.</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <button className="btn-secondary" disabled={busy} type="button" onClick={() => load().catch((e) => setError(getApiErrorMessage(e)))}>Refresh roster</button>
    <button className="btn-primary" disabled={busy || closed || !ready || !selected.length} type="button" onClick={invite}>{busy ? "Inviting…" : `Invite ${selected.length} selected`}</button>
    <div className="roster-table"><table><thead><tr><th><input type="checkbox" aria-label="Select all eligible learners" disabled={busy || closed || !ready || !rows.some((r) => !r.participant_id)} checked={rows.some((r) => !r.participant_id) && rows.filter((r) => !r.participant_id).every((r) => selected.includes(r.user_id))} onChange={(e) => setSelected(e.target.checked ? rows.filter((r) => !r.participant_id).map((r) => r.user_id) : [])} /></th><th>Learner</th><th>Programme</th><th>Session status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.user_id}><td><input type="checkbox" aria-label={`Invite ${row.name}`} disabled={busy || closed || !!row.participant_id} checked={selected.includes(row.user_id)} onChange={(e) => setSelected((old) => e.target.checked ? [...old, row.user_id] : old.filter((id) => id !== row.user_id))} /></td><td>{row.name}<small>{row.roll_number}</small></td><td>{row.academic_program || "—"}</td><td>{row.status.replaceAll("_", " ")}</td></tr>)}</tbody></table>{ready && !rows.length && <p>No eligible active enrollments in this course.</p>}</div>
  </details>;
}
