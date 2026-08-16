import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useId, useState } from "react";
import { ArrowRightIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import AuthShell from "../components/auth/AuthShell";
import styles from "../components/auth/Auth.module.css";
import { getMe, loginUser } from "../src/api";
import { clearSession, getToken, roleLandingPath, setToken } from "../src/auth";


const NOTICE_COPY = {
  expired: "Your session expired. Please log in again.",
  "signed-out": "You have been securely logged out.",
  unauthorized: "Please log in with an account that can access that page.",
  registered: "Registration complete. Log in with your new SYS account.",
  "password-reset": "Password updated. Log in with your new password.",
};

function loginErrorMessage(error) {
  if (!error?.response) {
    return "SYS could not reach the sign-in service. Check your connection and try again.";
  }
  if (error.response.status === 401 || error.response.status === 403) {
    return "The login identifier or password is incorrect.";
  }
  if (error.response.status >= 500) {
    return "The sign-in service is temporarily unavailable. Please try again shortly.";
  }
  return "The login identifier or password is incorrect.";
}

export default function LoginPage() {
  const router = useRouter();
  const identifierId = useId();
  const passwordId = useId();
  const errorId = useId();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function checkSession() {
      if (!getToken()) {
        if (active) setCheckingSession(false);
        return;
      }
      try {
        const { data: user } = await getMe();
        const destination = roleLandingPath(user?.role);
        if (destination) {
          await router.replace(destination);
          return;
        }
        clearSession();
        if (active) setError("This account does not have a supported SYS role.");
      } catch (sessionError) {
        clearSession();
        if (active && sessionError?.response?.status === 401) {
          await router.replace("/login?reason=expired");
        } else if (active) {
          setError("Your saved session could not be verified. Please log in again.");
        }
      } finally {
        if (active) setCheckingSession(false);
      }
    }

    checkSession();
    return () => { active = false; };
  }, [router]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);

    try {
      const { data: tokenData } = await loginUser({
        username: identifier.trim(),
        password,
      });
      const tokenType = typeof tokenData?.token_type === "string" ? tokenData.token_type.toLowerCase() : "";
      if (
        typeof tokenData?.access_token !== "string"
        || !tokenData.access_token.trim()
        || tokenType !== "bearer"
        || !setToken(tokenData.access_token)
      ) {
        throw new Error("INVALID_AUTH_RESPONSE");
      }
      const { data: user } = await getMe();
      const destination = roleLandingPath(user?.role);
      if (!destination) {
        clearSession();
        setError("This account does not have a supported SYS role.");
        return;
      }
      await router.replace(destination);
    } catch (loginError) {
      clearSession();
      setError(
        loginError?.message === "INVALID_AUTH_RESPONSE"
          ? "The sign-in service returned an invalid response. Please try again."
          : loginErrorMessage(loginError),
      );
    } finally {
      setPassword("");
      setSubmitting(false);
    }
  }

  const reason = typeof router.query.reason === "string" ? router.query.reason : "";
  const notice = NOTICE_COPY[reason];

  return (
    <>
      <Head>
        <title>Login | SYS – Strengthen Your Skills</title>
        <meta name="description" content="Secure unified login for SYS students, faculty and administrators." />
      </Head>
      <AuthShell
        introTitle="One secure entry to your SYS workspace."
        introDescription="Students, faculty and administrators use the same login. SYS verifies your active account before opening the workspace assigned to your role."
      >
        <div className={styles.formHeading}>
          <p className={styles.formEyebrow}>Welcome to SYS</p>
          <h2 id="login-title">Log in to continue</h2>
          <p>Use any verified identifier linked to your active SYS account.</p>
        </div>

        {notice && <div className={styles.notice} role="status">{notice}</div>}
        {error && <div id={errorId} className={styles.error} role="alert">{error}</div>}

        {checkingSession ? (
          <div className={styles.sessionCheck} role="status" aria-live="polite">
            <span className={styles.spinner} aria-hidden="true" />
            Checking your session…
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit} aria-describedby={error ? errorId : undefined}>
            <div className={styles.fieldGroup}>
              <label htmlFor={identifierId}>Email address, mobile number or institutional ID</label>
              <input
                id={identifierId}
                name="username"
                type="text"
                autoComplete="username"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="Email, +91 mobile, roll number or employee code"
                required
                disabled={submitting}
              />
              <p>Personal mobile numbers must include the country code, for example +919876543210.</p>
            </div>

            <div className={styles.fieldGroup}>
              <label htmlFor={passwordId}>Password</label>
              <div className={styles.passwordField}>
                <input
                  id={passwordId}
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={submitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  disabled={submitting}
                >
                  {showPassword ? <EyeSlashIcon aria-hidden="true" /> : <EyeIcon aria-hidden="true" />}
                </button>
              </div>
            </div>

            <button className={styles.submitButton} type="submit" disabled={submitting}>
              {submitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
              {submitting ? "Verifying account…" : "Login to SYS"}
              {!submitting ? <ArrowRightIcon aria-hidden="true" /> : null}
            </button>
          </form>
        )}

        <nav className={styles.authLinks} aria-label="Account actions">
          <Link href="/register">New to SYS? Register your account</Link>
          <Link href="/forgot-password">Forgot password?</Link>
          <Link href="/account-help">Need account help?</Link>
        </nav>
      </AuthShell>
    </>
  );
}

LoginPage.getLayout = (page) => page;
