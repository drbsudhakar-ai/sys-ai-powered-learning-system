import Head from "next/head";
import { useEffect, useState } from "react";
import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import { getAIProviderSettings, saveAIProviderSettings, testAIProviderConnection, getAIUsage, getApiErrorMessage } from "../../src/api";
import styles from "./AIProviderWorkspace.module.css";

const numbers = [
  ["daily_requests", "Requests / UTC day", 1, 1000000],
  ["daily_tokens", "Tokens / UTC day", 1000, 1000000000],
  ["minute_requests", "Requests / rolling minute", 1, 10000],
  ["minute_tokens", "Tokens / rolling minute", 1000, 10000000],
  ["student_daily_requests", "Live requests / student / day", 1, 10000],
  ["max_output_tokens", "Maximum output tokens / request", 128, 8192],
];
const count = (value) => Number(value || 0).toLocaleString();

export default function AIProviderWorkspace() {
  const access = useAdminAccess();
  const [config, setConfig] = useState(null);
  const [usage, setUsage] = useState(null);
  const [secret, setSecret] = useState("");
  const [clearKey, setClearKey] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    const [settings, summary] = await Promise.all([getAIProviderSettings(), getAIUsage()]);
    setConfig(settings.data); setUsage(summary.data); setSecret(""); setClearKey(false); setDirty(false);
  }
  useEffect(() => { if (access.status === "ready") load().catch((e) => setError(getApiErrorMessage(e, "Unable to load AI settings."))); }, [access.status]);
  function change(name, value) { setConfig((old) => ({ ...old, [name]: value })); setDirty(true); setNotice(""); }
  async function save(event) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    const payload = Object.fromEntries(["label", "protocol", "base_url", "model", "enabled", ...numbers.map(([key]) => key)].map((key) => [key, config[key]]));
    payload.expected_revision = config.revision; payload.clear_api_key = clearKey;
    if (secret.trim()) payload.api_key = secret.trim();
    try {
      const { data } = await saveAIProviderSettings(payload);
      setConfig(data); setSecret(""); setClearKey(false); setDirty(false); setNotice("Settings saved. New AI requests use this configuration.");
      setUsage((await getAIUsage()).data);
    } catch (e) { setError(getApiErrorMessage(e, "Unable to save AI settings.")); }
    finally { setBusy(false); }
  }
  async function test() {
    setBusy(true); setError(""); setNotice("");
    try { const { data } = await testAIProviderConnection(); setNotice(data.message); }
    catch (e) { setError(getApiErrorMessage(e, "Provider test failed.")); }
    finally { try { setUsage((await getAIUsage()).data); } catch { /* Preserve the connection result. */ } setBusy(false); }
  }
  async function refresh() {
    setBusy(true); setError("");
    try { setUsage((await getAIUsage()).data); }
    catch (e) { setError(getApiErrorMessage(e, "Usage refresh failed.")); }
    finally { setBusy(false); }
  }
  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing AI administration." />;
  if (access.status !== "ready") return access.status === "error" ? <BrandedState type="error" title="Access unavailable" message={access.error} /> : null;
  return <><Head><title>AI Provider & Usage | SYS</title></Head><AdminShell user={access.user} breadcrumb="AI Administration" pageTitle="AI Provider & Usage" scopeLabel="Platform-wide">
    <main className={styles.workspace}>
      <header className={styles.hero}><span>SYS · AI OPERATIONS</span><h1>AI Provider & Usage</h1><p>One teaching platform. Configurable providers. Controlled pilot usage.</p></header>
      {error && <div className={styles.error} role="alert">{error}<button type="button" disabled={busy} onClick={() => { if (!dirty || window.confirm("Discard unsaved settings and reload?")) { setBusy(true); load().catch((e) => setError(getApiErrorMessage(e))).finally(() => setBusy(false)); } }}>Reload settings</button></div>}
      {notice && <div className={styles.notice} role="status">{notice}</div>}
      {!config && !error && <p role="status">Loading provider settings…</p>}
      {config && <form onSubmit={save} className={styles.card}>
        <div className={styles.titleRow}><div><h2>Provider connection</h2><p>Credentials are encrypted on the server and are never returned to this page.</p></div><span className={styles.badge}>{config.enabled ? "Live AI enabled" : "Live AI disabled"}{dirty ? " · Unsaved" : ""}</span></div>
        {config.runtime_mode !== "configured" && <div className={styles.warning}>Server override: {config.runtime_mode}. Set SYS_AI_PROVIDER=configured for classroom requests to use these settings. Mock and echo are offline development modes, not real AI.</div>}
        {!config.encryption_ready && <div className={styles.warning}>Server setup needed: configure SYS_AI_ENCRYPTION_KEY before saving hosted-provider credentials.</div>}
        <fieldset disabled={busy} className={styles.fields}>
          <label>Connection label<input required maxLength={100} value={config.label} onChange={(e) => change("label", e.target.value)} /></label>
          <label>API protocol<select value={config.protocol} onChange={(e) => { change("protocol", e.target.value); change("base_url", e.target.value === "ollama" ? config.ollama_base_url : config.approved_base_urls[0] || ""); setSecret(""); }}><option value="openai_compatible">OpenAI-compatible (Groq and others)</option><option value="ollama">Ollama (self-hosted)</option></select></label>
          <label>Approved base URL<select required value={config.base_url} onChange={(e) => { change("base_url", e.target.value); setSecret(""); }}><option value="" disabled>Select an approved endpoint</option>{[...new Set([config.base_url, ...(config.protocol === "ollama" ? [config.ollama_base_url] : config.approved_base_urls)])].filter(Boolean).map((url) => <option key={url} value={url}>{url}</option>)}</select></label>
          <label>Model ID<input required maxLength={160} value={config.model} onChange={(e) => change("model", e.target.value)} placeholder="Exact model ID from your provider console" /></label>
          <label>API key {config.has_api_key ? "(stored securely)" : "(not stored)"}<input type="password" autoComplete="new-password" maxLength={4096} value={secret} onChange={(e) => { setSecret(e.target.value); setDirty(true); }} placeholder={config.has_api_key ? "Leave blank to retain existing key" : "Enter provider API key"} /></label>
          <div className={styles.checks}><label><input type="checkbox" checked={clearKey} onChange={(e) => { setClearKey(e.target.checked); setDirty(true); }} />Remove stored key on save</label><label><input type="checkbox" checked={config.enabled} onChange={(e) => change("enabled", e.target.checked)} />Enable live lesson generation and explanations</label></div>
        </fieldset>
        <p className={styles.help}>Changing endpoint or protocol clears the previous credential. New endpoints require server-operator approval. Providers with a different API format need an adapter; model compatibility must be tested.</p>
        <h2>Pilot budgets</h2><p>Shared across the application, not multiplied by student count. Start conservatively for 20–25 students.</p>
        <fieldset disabled={busy} className={styles.fields}>{numbers.map(([key, label, min, max]) => <label key={key}>{label}<input type="number" required min={min} max={max} step="1" value={config[key]} onChange={(e) => change(key, e.target.value === "" ? "" : Number(e.target.value))} /></label>)}</fieldset>
        <p className={styles.help}>SYS reserves a conservative token estimate before a request. Provider limits may be lower and may change. These are local safety budgets—not a guarantee of free usage or remaining provider quota.</p>
        <div className={styles.actions}><button type="submit" disabled={busy}>{busy ? "Working…" : "Save configuration"}</button><button type="button" disabled={busy || dirty || !config.revision} onClick={test}>Test saved connection</button><span>The test consumes one request, even when live AI is disabled.</span></div>
      </form>}
      <section className={styles.card} aria-label="Administrator AI usage panel"><div className={styles.titleRow}><div><h2>Usage panel</h2><p>{usage ? `UTC day: ${usage.date_utc}` : "Loading usage…"}</p></div><button type="button" disabled={busy} onClick={refresh}>Refresh usage</button></div>
        {usage && <>{(usage.requests >= usage.limits.daily_requests * .8 || usage.budget_tokens >= usage.limits.daily_tokens * .8) && <div className={styles.warning}>At least 80% of a daily SYS budget is consumed or reserved. Check usage before scheduling more live sessions.</div>}<div className={styles.metrics}>
          <article><span>Requests today</span><strong>{count(usage.requests)} / {count(usage.limits.daily_requests)}</strong></article>
          <article><span>Budget tokens consumed / reserved</span><strong>{count(usage.budget_tokens)} / {count(usage.limits.daily_tokens)}</strong></article>
          <article><span>Provider-reported tokens</span><strong>{count(usage.measured_tokens)}</strong></article>
          <article><span>Failed requests</span><strong>{count(usage.failed_requests)}</strong></article>
        </div><p className={styles.help}>{count(usage.estimated_requests)} requests use estimates or pending reservations. Failed requests may consume provider quota. Interrupted requests retain their reservation until the UTC daily reset. Monetary cost is not calculated.</p>
        <div className={styles.purposes}>{usage.by_purpose.map((row) => <span key={row.purpose}>{row.purpose}: {count(row.requests)} requests</span>)}</div>
        <h3>Usage by account today · top 100 by budget tokens</h3><div className={styles.tableWrap}><table><thead><tr><th>Account</th><th>Role</th><th>Requests</th><th>Budget tokens</th></tr></thead><tbody>{usage.by_user.length ? usage.by_user.map((row) => <tr key={row.user_id}><td>{row.name}<small>ID {row.user_id}</small></td><td>{row.role}</td><td>{count(row.requests)}</td><td>{count(row.budget_tokens)}</td></tr>) : <tr><td colSpan={4}>No account usage recorded today.</td></tr>}</tbody></table></div>
        <h3>Recent requests · latest 50</h3><div className={styles.tableWrap}><table><thead><tr><th>Time (UTC)</th><th>Provider / model</th><th>Purpose</th><th>Status</th><th>Tokens</th></tr></thead><tbody>{usage.recent.length ? usage.recent.map((row) => <tr key={row.id}><td>{row.created_at.replace("T", " ").slice(0, 19)}</td><td>{row.provider_label}<small>{row.model}</small></td><td>{row.purpose}</td><td>{row.status}<small>{row.error_code || `Ref ${row.id}`}</small></td><td>{count(row.total_tokens ?? row.budget_tokens)}<small>{row.total_tokens == null ? "Estimate / reservation" : "Provider reported"}</small></td></tr>) : <tr><td colSpan={5}>No live requests recorded yet.</td></tr>}</tbody></table></div></>}
        <p className={styles.help}>This panel records requests routed through the SYS AI gateway only. It does not store prompts, answers or API keys. Course management, saved assessments, tracking and ordinary reports do not consume this AI budget.</p>
      </section>
    </main></AdminShell></>;
}
