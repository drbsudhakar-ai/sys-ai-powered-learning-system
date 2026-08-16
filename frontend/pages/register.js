import Head from "next/head";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import AuthShell from "../components/auth/AuthShell";
import OtpInput from "../components/auth/OtpInput";
import styles from "../components/auth/Auth.module.css";
import {
  completeActivation,
  startActivation,
  verifyActivationContact,
  verifyActivationOtp,
} from "../src/api";


const SAFE_REGISTRATION_ERROR = "We couldn’t verify this institutional ID for registration. Check the details or contact your SYS administrator.";

function apiMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && !detail.toLowerCase().includes("password")) return detail;
  return fallback;
}

export default function RegisterPage() {
  const roleId = useId();
  const institutionalId = useId();
  const emailId = useId();
  const mobileId = useId();
  const passwordId = useId();
  const confirmId = useId();
  const [phase, setPhase] = useState("identity");
  const [role, setRole] = useState("student");
  const [identifier, setIdentifier] = useState("");
  const [ownershipChannel, setOwnershipChannel] = useState("email");
  const [challengeId, setChallengeId] = useState("");
  const [otp, setOtp] = useState("");
  const [ownershipAuthorization, setOwnershipAuthorization] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [emailAuthorization, setEmailAuthorization] = useState("");
  const [mobileAuthorization, setMobileAuthorization] = useState("");
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

  function beginRequest() {
    setSubmitting(true);
    setError("");
    setNotice("");
  }

  function finishRequest() {
    setSubmitting(false);
  }

  async function requestOwnership(event) {
    event?.preventDefault();
    if (submitting) return;
    beginRequest();
    try {
      const { data } = await startActivation({
        role,
        institutional_id: identifier.trim(),
        channel: ownershipChannel,
      });
      setChallengeId(data.challenge_id);
      setOtp("");
      setPhase("ownership");
      setResendSeconds(60);
      setNotice("If the institutional details are eligible, a verification code has been sent to the contact already recorded by your administrator.");
    } catch (requestError) {
      setError(apiMessage(requestError, SAFE_REGISTRATION_ERROR));
    } finally {
      finishRequest();
    }
  }

  async function verifyOwnership(event) {
    event.preventDefault();
    if (submitting || otp.length !== 6) return;
    beginRequest();
    try {
      const { data } = await verifyActivationOtp({ challenge_id: challengeId, code: otp });
      setOwnershipAuthorization(data.authorization);
      setOtp("");
      setPhase("contacts");
    } catch {
      setError(SAFE_REGISTRATION_ERROR);
    } finally {
      finishRequest();
    }
  }

  async function requestContactOtp(contactType, contactValue) {
    const { data } = await verifyActivationContact({
      action: "send",
      ownership_authorization: ownershipAuthorization,
      contact_type: contactType,
      contact_value: contactValue,
    });
    setChallengeId(data.challenge_id);
    setOtp("");
    setResendSeconds(60);
  }

  async function submitContacts(event) {
    event.preventDefault();
    if (submitting) return;
    beginRequest();
    try {
      await requestContactOtp("email", email.trim().toLowerCase());
      setPhase("emailOtp");
      setNotice("Enter the code sent to the personal email address you provided.");
    } catch (requestError) {
      setError(apiMessage(requestError, "Your contact details could not be verified. Check them and try again."));
    } finally {
      finishRequest();
    }
  }

  async function verifyEmail(event) {
    event.preventDefault();
    if (submitting || otp.length !== 6) return;
    beginRequest();
    try {
      const { data } = await verifyActivationContact({
        action: "verify",
        ownership_authorization: ownershipAuthorization,
        contact_type: "email",
        challenge_id: challengeId,
        code: otp,
      });
      setEmailAuthorization(data.authorization);
      await requestContactOtp("mobile", mobile);
      setPhase("mobileOtp");
      setNotice("Email verified. Enter the code sent to your personal mobile number.");
    } catch (requestError) {
      setError(apiMessage(requestError, "The verification code is invalid or expired."));
    } finally {
      finishRequest();
    }
  }

  async function verifyMobile(event) {
    event.preventDefault();
    if (submitting || otp.length !== 6) return;
    beginRequest();
    try {
      const { data } = await verifyActivationContact({
        action: "verify",
        ownership_authorization: ownershipAuthorization,
        contact_type: "mobile",
        challenge_id: challengeId,
        code: otp,
      });
      setMobileAuthorization(data.authorization);
      setOtp("");
      setPhase("password");
    } catch (requestError) {
      setError(apiMessage(requestError, "The verification code is invalid or expired."));
    } finally {
      finishRequest();
    }
  }

  async function resendCurrentOtp() {
    if (resendSeconds > 0 || submitting) return;
    beginRequest();
    try {
      if (phase === "ownership") {
        await requestOwnership();
      } else if (phase === "emailOtp") {
        await requestContactOtp("email", email.trim().toLowerCase());
      } else if (phase === "mobileOtp") {
        await requestContactOtp("mobile", mobile);
      }
      setNotice("A new verification code has been requested. Previous codes are no longer valid.");
    } catch (requestError) {
      setError(apiMessage(requestError, "A new code could not be requested yet."));
    } finally {
      finishRequest();
    }
  }

  async function finishRegistration(event) {
    event.preventDefault();
    if (submitting) return;
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    beginRequest();
    try {
      await completeActivation({
        ownership_authorization: ownershipAuthorization,
        email: email.trim().toLowerCase(),
        email_authorization: emailAuthorization,
        mobile_number: mobile,
        mobile_authorization: mobileAuthorization,
        password,
        confirm_password: confirmPassword,
      });
      setPassword("");
      setConfirmPassword("");
      setPhase("success");
    } catch (requestError) {
      setError(apiMessage(requestError, "Registration could not be completed. Contact your SYS administrator."));
      setPassword("");
      setConfirmPassword("");
    } finally {
      finishRequest();
    }
  }

  const step = phase === "identity" ? 1 : phase === "ownership" ? 2 : phase === "contacts" || phase.endsWith("Otp") ? 3 : 4;

  return (
    <>
      <Head>
        <title>Register your account | SYS</title>
        <meta name="description" content="Controlled SYS account activation for pre-authorized students and faculty." />
      </Head>
      <AuthShell
        introTitle="Activate the SYS account prepared for you."
        introDescription="Registration is limited to student and faculty records already added by a SYS administrator. Institutional identity and personal contacts are verified before credentials are created."
      >
        <div className={styles.formHeading}>
          <p className={styles.formEyebrow}>Controlled registration</p>
          <h2 id={`${roleId}-title`}>{phase === "success" ? "Your account is ready" : "Register your account"}</h2>
          <p>Registration is available only to students and faculty whose institutional details have already been added by the SYS administrator.</p>
        </div>

        {phase !== "success" && (
          <ol className={styles.stepper} aria-label={`Registration step ${step} of 4`}>
            {["Identity", "Ownership", "Contacts", "Password"].map((label, index) => (
              <li key={label} className={index + 1 <= step ? styles.stepActive : ""}>
                <span>{index + 1}</span>{label}
              </li>
            ))}
          </ol>
        )}

        {notice && <div className={styles.notice} role="status">{notice}</div>}
        {error && <div className={styles.error} role="alert">{error}</div>}

        {phase === "identity" && (
          <form className={styles.form} onSubmit={requestOwnership}>
            <fieldset className={styles.choiceFieldset}>
              <legend>Select your SYS role</legend>
              <div className={styles.roleChoice}>
                {[["student", "Student"], ["faculty", "Faculty"]].map(([value, label]) => (
                  <label key={value}>
                    <input type="radio" name="role" value={value} checked={role === value} onChange={() => setRole(value)} />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className={styles.fieldGroup}>
              <label htmlFor={institutionalId}>{role === "student" ? "Roll Number" : "Employee Code"}</label>
              <input id={institutionalId} value={identifier} onChange={(event) => setIdentifier(event.target.value)} required disabled={submitting} autoComplete="off" />
            </div>
            <fieldset className={styles.choiceFieldset}>
              <legend>Send ownership code to the contact on record</legend>
              <div className={styles.channelChoice}>
                {[["email", "Email"], ["mobile", "Mobile"]].map(([value, label]) => (
                  <label key={value}>
                    <input type="radio" name="channel" value={value} checked={ownershipChannel === value} onChange={() => setOwnershipChannel(value)} />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <button className={styles.submitButton} type="submit" disabled={submitting}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              Verify eligibility <ArrowRightIcon aria-hidden="true" />
            </button>
          </form>
        )}

        {phase === "ownership" && (
          <OtpStep title="Verify institutional ownership" otp={otp} setOtp={setOtp} onSubmit={verifyOwnership} onResend={resendCurrentOtp} resendSeconds={resendSeconds} submitting={submitting} />
        )}

        {phase === "contacts" && (
          <form className={styles.form} onSubmit={submitContacts}>
            <div className={styles.fieldGroup}>
              <label htmlFor={emailId}>Personal email address</label>
              <input id={emailId} type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={submitting} />
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={mobileId}>Personal mobile number</label>
              <input id={mobileId} type="tel" autoComplete="tel" placeholder="+919876543210" value={mobile} onChange={(event) => setMobile(event.target.value)} required disabled={submitting} />
              <p>Use your unique personal mobile in E.164 format. Do not use a shared or guardian number as a login identifier.</p>
            </div>
            <button className={styles.submitButton} type="submit" disabled={submitting}>
              Send contact verification codes <ArrowRightIcon aria-hidden="true" />
            </button>
          </form>
        )}

        {phase === "emailOtp" && (
          <OtpStep title="Verify your personal email" otp={otp} setOtp={setOtp} onSubmit={verifyEmail} onResend={resendCurrentOtp} resendSeconds={resendSeconds} submitting={submitting} />
        )}
        {phase === "mobileOtp" && (
          <OtpStep title="Verify your personal mobile" otp={otp} setOtp={setOtp} onSubmit={verifyMobile} onResend={resendCurrentOtp} resendSeconds={resendSeconds} submitting={submitting} />
        )}

        {phase === "password" && (
          <form className={styles.form} onSubmit={finishRegistration}>
            <div className={styles.fieldGroup}>
              <label htmlFor={passwordId}>Create password</label>
              <div className={styles.passwordField}>
                <input id={passwordId} type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required disabled={submitting} />
                <button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                  {showPassword ? <EyeSlashIcon aria-hidden="true" /> : <EyeIcon aria-hidden="true" />}
                </button>
              </div>
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor={confirmId}>Confirm password</label>
              <input id={confirmId} type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required disabled={submitting} />
            </div>
            <button className={styles.submitButton} type="submit" disabled={submitting}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              Complete registration <ArrowRightIcon aria-hidden="true" />
            </button>
          </form>
        )}

        {phase === "success" && (
          <div className={styles.successPanel} role="status">
            <p>Your student or faculty role was securely derived from the institutional record you claimed.</p>
            <Link href="/login?reason=registered" className={styles.submitButton}>Continue to login <ArrowRightIcon aria-hidden="true" /></Link>
          </div>
        )}

        {phase !== "success" && (
          <p className={styles.backLink}><ArrowLeftIcon aria-hidden="true" /><Link href="/login">Back to login</Link></p>
        )}
      </AuthShell>
    </>
  );
}

function OtpStep({ title, otp, setOtp, onSubmit, onResend, resendSeconds, submitting }) {
  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <p className={styles.stepTitle}>{title}</p>
      <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
      <button className={styles.submitButton} type="submit" disabled={submitting || otp.length !== 6}>
        {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
        Verify code <ArrowRightIcon aria-hidden="true" />
      </button>
      <button className={styles.resendButton} type="button" onClick={onResend} disabled={submitting || resendSeconds > 0}>
        {resendSeconds > 0 ? `Request another code in ${resendSeconds}s` : "Request another code"}
      </button>
      <p className={styles.fieldHelp}>Codes expire after 10 minutes. If no usable contact is on record, contact your SYS administrator.</p>
    </form>
  );
}

RegisterPage.getLayout = (page) => page;
