import Head from "next/head";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import AuthShell from "../components/auth/AuthShell";
import OtpInput from "../components/auth/OtpInput";
import styles from "../components/auth/Auth.module.css";
import {
  completePasswordReset,
  startPasswordReset,
  verifyPasswordResetOtp,
} from "../src/api";


const GENERIC_RECOVERY = "If the details match an active SYS account, a verification code has been sent.";

export default function ForgotPasswordPage() {
  const identifierId = useId();
  const passwordId = useId();
  const confirmId = useId();
  const [phase, setPhase] = useState("identifier");
  const [identifier, setIdentifier] = useState("");
  const [channel, setChannel] = useState("email");
  const [challengeId, setChallengeId] = useState("");
  const [otp, setOtp] = useState("");
  const [resetAuthorization, setResetAuthorization] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);

  useEffect(() => {
    if (resendSeconds <= 0) return undefined;
    const timer = window.setInterval(() => {
      setResendSeconds((seconds) => Math.max(0, seconds - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendSeconds]);

  async function requestReset(event) {
    event?.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const { data } = await startPasswordReset({ identifier: identifier.trim(), channel });
      setChallengeId(data.challenge_id);
      setOtp("");
      setNotice(GENERIC_RECOVERY);
      setResendSeconds(60);
      setPhase("otp");
    } catch {
      setNotice(GENERIC_RECOVERY);
      setResendSeconds(60);
      setPhase("otp");
    } finally {
      setSubmitting(false);
    }
  }

  async function verifyOtp(event) {
    event.preventDefault();
    if (submitting || otp.length !== 6) return;
    setSubmitting(true);
    setError("");
    try {
      const { data } = await verifyPasswordResetOtp({ challenge_id: challengeId, code: otp });
      setResetAuthorization(data.authorization);
      setOtp("");
      setNotice("");
      setPhase("password");
    } catch {
      setError("The verification code is invalid or expired.");
    } finally {
      setSubmitting(false);
    }
  }

  async function resendOtp() {
    if (resendSeconds > 0 || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const { data } = await startPasswordReset({ identifier: identifier.trim(), channel });
      setChallengeId(data.challenge_id);
      setOtp("");
      setNotice(GENERIC_RECOVERY);
      setResendSeconds(60);
    } catch {
      setNotice(GENERIC_RECOVERY);
      setResendSeconds(60);
    } finally {
      setSubmitting(false);
    }
  }

  async function savePassword(event) {
    event.preventDefault();
    if (submitting) return;
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await completePasswordReset({
        reset_authorization: resetAuthorization,
        password,
        confirm_password: confirmPassword,
      });
      setPassword("");
      setConfirmPassword("");
      setResetAuthorization("");
      setPhase("success");
    } catch (resetError) {
      const detail = resetError?.response?.data?.detail;
      setError(typeof detail === "string" && !detail.toLowerCase().includes("password") ? detail : "Password reset could not be completed. Start again or contact your SYS administrator.");
      setPassword("");
      setConfirmPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Head>
        <title>Forgot password | SYS</title>
        <meta name="description" content="Secure SYS password recovery with verified email or mobile OTP." />
      </Head>
      <AuthShell
        introTitle="Recover access without exposing your account."
        introDescription="SYS uses the verified email or unique personal mobile already linked to an active account. Recovery responses never reveal whether an identifier exists."
      >
        <div className={styles.formHeading}>
          <p className={styles.formEyebrow}>Secure account recovery</p>
          <h2>{phase === "success" ? "Password updated" : "Forgot password?"}</h2>
          <p>{phase === "identifier" ? "Enter any login identifier you know." : "Complete the verification steps to create a new password."}</p>
        </div>

        {notice && <div className={styles.notice} role="status">{notice}</div>}
        {error && <div className={styles.error} role="alert">{error}</div>}

        {phase === "identifier" && (
          <form className={styles.form} onSubmit={requestReset}>
            <div className={styles.fieldGroup}>
              <label htmlFor={identifierId}>Known login identifier</label>
              <input id={identifierId} type="text" autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="Email, +91 mobile, roll number or employee code" required disabled={submitting} />
            </div>
            <fieldset className={styles.choiceFieldset}>
              <legend>Receive verification code by</legend>
              <div className={styles.channelChoice}>
                {[["email", "Verified email"], ["mobile", "Verified mobile"]].map(([value, label]) => (
                  <label key={value}>
                    <input type="radio" name="channel" value={value} checked={channel === value} onChange={() => setChannel(value)} />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <button className={styles.submitButton} type="submit" disabled={submitting}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              Send verification code <ArrowRightIcon aria-hidden="true" />
            </button>
          </form>
        )}

        {phase === "otp" && (
          <form className={styles.form} onSubmit={verifyOtp}>
            <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
            <button className={styles.submitButton} type="submit" disabled={submitting || otp.length !== 6}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              Verify code <ArrowRightIcon aria-hidden="true" />
            </button>
            <button className={styles.resendButton} type="button" onClick={resendOtp} disabled={submitting || resendSeconds > 0}>
              {resendSeconds > 0 ? `Request another code in ${resendSeconds}s` : "Request another code"}
            </button>
            <p className={styles.fieldHelp}>Codes expire after 10 minutes and can be used only once.</p>
          </form>
        )}

        {phase === "password" && (
          <form className={styles.form} onSubmit={savePassword}>
            <div className={styles.fieldGroup}>
              <label htmlFor={passwordId}>New password</label>
              <div className={styles.passwordField}>
                <input id={passwordId} type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required disabled={submitting} />
                <button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                  {showPassword ? <EyeSlashIcon aria-hidden="true" /> : <EyeIcon aria-hidden="true" />}
                </button>
              </div>
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={confirmId}>Confirm new password</label>
              <input id={confirmId} type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required disabled={submitting} />
            </div>
            <button className={styles.submitButton} type="submit" disabled={submitting}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              Update password <ArrowRightIcon aria-hidden="true" />
            </button>
          </form>
        )}

        {phase === "success" && (
          <div className={styles.successPanel} role="status">
            <p>Existing sessions have been invalidated. Log in normally with your new password.</p>
            <Link href="/login?reason=password-reset" className={styles.submitButton}>Return to login <ArrowRightIcon aria-hidden="true" /></Link>
          </div>
        )}

        {phase !== "success" && (
          <div className={styles.secondaryLinks}>
            <p className={styles.backLink}><ArrowLeftIcon aria-hidden="true" /><Link href="/login">Back to login</Link></p>
            <Link href="/account-help">Need account help?</Link>
          </div>
        )}
      </AuthShell>
    </>
  );
}

ForgotPasswordPage.getLayout = (page) => page;
