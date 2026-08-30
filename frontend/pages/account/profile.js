import Head from "next/head";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import { CameraIcon, CheckCircleIcon, IdentificationIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import { getApiErrorMessage, getMe, removeMyProfilePhoto, updateMyProfile, uploadMyProfilePhoto } from "../../src/api";
import { clearSession, getToken } from "../../src/auth";
import styles from "../../components/account/SelfProfile.module.css";

function field(label, value) {
  return <div className={styles.field}><span>{label}</span><strong>{value || "Not recorded"}</strong></div>;
}

export default function SelfProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [mobile, setMobile] = useState("");
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!getToken()) { router.replace("/login?reason=unauthorized"); return; }
    getMe().then(({ data }) => {
      if (!["student", "faculty"].includes(data?.role)) { router.replace("/dashboard"); return; }
      setUser(data); setMobile(data.mobile_number || "");
    }).catch((requestError) => {
      if (requestError?.response?.status === 401) { clearSession(); router.replace("/login?reason=expired"); return; }
      setError(getApiErrorMessage(requestError, "Your profile could not be loaded."));
    });
  }, [router]);

  useEffect(() => {
    if (!photo) { setPreview(""); return undefined; }
    const url = URL.createObjectURL(photo); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const identifier = user?.role === "faculty" ? user?.employee_code : user?.roll_number;
  const academic = useMemo(() => user?.role === "faculty" ? ["Department", user?.department, "Designation", user?.designation, "Employment status", user?.employment_status] : ["Academic programme", user?.academic_program, "Present year", user?.present_year, "Academic status", user?.academic_status], [user]);

  async function save(event) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      let current = (await updateMyProfile({ mobile_number: mobile || null })).data;
      if (photo) current = (await uploadMyProfilePhoto(photo)).data;
      setUser(current); setMobile(current.mobile_number || ""); setPhoto(null);
      setNotice("Your profile was updated successfully.");
      window.dispatchEvent(new CustomEvent("sys:profile-updated"));
    } catch (requestError) { setError(getApiErrorMessage(requestError, "Your profile could not be updated.")); }
    finally { setBusy(false); }
  }

  async function removePhoto() {
    setBusy(true); setError(""); setNotice("");
    try { const { data } = await removeMyProfilePhoto(); setUser(data); setPhoto(null); setNotice("Your profile photograph was removed."); window.dispatchEvent(new CustomEvent("sys:profile-updated")); }
    catch (requestError) { setError(getApiErrorMessage(requestError, "The photograph could not be removed.")); }
    finally { setBusy(false); }
  }

  return <>
    <Head><title>My Profile | SYS</title></Head>
    <main className={`${styles.page} role-page`}>
      <p className={styles.eyebrow}>PEOPLE &amp; ACCESS · MY SYS PROFILE</p>
      <div className={styles.heading}><div><h1>My profile</h1><p>Review your institutional identity and maintain your personal contact and photograph.</p></div><span>{user?.account_status === "ACTIVE" ? "Active SYS account" : "Account pending"}</span></div>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {notice ? <div className={styles.success}><CheckCircleIcon />{notice}</div> : null}
      {!user ? <div className={styles.loading}>Loading your authorized SYS profile…</div> : <form className={styles.form} onSubmit={save}>
        <section className={styles.banner}>
          <label className={styles.photo}>
            {preview || user.photo_url ? <img src={preview || user.photo_url} alt={`${user.name} profile`} /> : <span>{String(user.name).split(/\s+/).map((part) => part[0]).slice(0,2).join("")}</span>}
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPhoto(event.target.files?.[0] || null)} />
            <em><CameraIcon />Change photograph</em>
          </label>
          <div><small>{user.role === "faculty" ? "FACULTY PROFILE" : "STUDENT PROFILE"}</small><h2>{user.name}</h2><p>{user.role === "faculty" ? `Employee code: ${identifier}` : `Roll number: ${identifier}`}</p><div className={styles.photoActions}>{user.photo_url ? <button type="button" onClick={removePhoto} disabled={busy}>Remove current photograph</button> : null}</div></div>
        </section>
        <div className={styles.columns}>
          <section className={styles.card}><header><IdentificationIcon /><div><h2>Institutional identity</h2><p>These master details can only be corrected by a SYS administrator.</p></div></header><div className={styles.fieldGrid}>{field("Full name", user.name)}{field(user.role === "faculty" ? "Employee code" : "Roll number", identifier)}{field("College", user.college)}{field(academic[0], academic[1])}{field(academic[2], academic[3])}{field(academic[4], academic[5])}</div></section>
          <section className={styles.card}><header><ShieldCheckIcon /><div><h2>Contact and account</h2><p>Your verified personal email is your SYS login username.</p></div></header><label className={styles.inputLabel}>Personal login email<input value={user.email || ""} readOnly /><small>Email changes require identity verification. Contact your SYS administrator until the verified email-change workflow is enabled.</small></label><label className={styles.inputLabel}>Personal mobile number<input value={mobile} onChange={(event) => setMobile(event.target.value)} placeholder="+919876543210" /><small>Use E.164 format. A changed number remains unverified until mobile OTP verification is available.</small></label><div className={styles.verification}><span>Email: {user.email_verified ? "Verified" : "Not verified"}</span><span>Mobile: {user.mobile_verified ? "Verified" : "Not verified"}</span></div></section>
        </div>
        <footer className={styles.actions}><button type="button" onClick={() => router.back()} disabled={busy}>Cancel</button><button type="submit" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button></footer>
      </form>}
    </main>
  </>;
}
