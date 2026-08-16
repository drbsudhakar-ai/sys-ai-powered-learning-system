import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useId, useState } from "react";
import {
  ArrowRightIcon,
  CheckCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { getMe, loginUser } from "../src/api";
import { clearSession, getToken, roleLandingPath, setToken } from "../src/auth";
import styles from "../components/auth/Auth.module.css";

const NOTICE_COPY = {
  expired: "Your session expired. Please log in again.",
  "registration-disabled": "Public registration is disabled. Contact your SYS administrator for account access.",
  "signed-out": "You have been securely logged out.",
  unauthorized: "Please log in with an account that can access that page.",
};

function loginErrorMessage(error) {
  if (!error?.response) {
    return "SYS could not reach the sign-in service. Check your connection and try again.";
  }
  if (error.response.status === 401) {
    return "The email address or password is incorrect.";
  }
  if (error.response.status === 403) {
    return "This account is inactive. Contact your SYS administrator for access.";
  }
  if (error.response.status >= 500) {
    return "The sign-in service is temporarily unavailable. Please try again shortly.";
  }
  return "Login could not be completed. Please check your details and try again.";
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
        if (user?.is_active !== true) {
          clearSession();
          if (active) setError("This account is inactive. Contact your SYS administrator for access.");
          return;
        }
        const destination = roleLandingPath(user.role);
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
    return () => {
      active = false;
    };
  }, [router]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    let tokenStored = false;

    try {
      const { data: tokenData } = await loginUser({
        username: identifier.trim(),
        password,
      });
      const tokenType = typeof tokenData?.token_type === "string" ? tokenData.token_type.toLowerCase() : "";
      if (typeof tokenData?.access_token !== "string" || !tokenData.access_token.trim() || tokenType !== "bearer") {
        const invalidResponse = new Error("Invalid authentication response");
        invalidResponse.code = "INVALID_AUTH_RESPONSE";
        throw invalidResponse;
      }
      if (!setToken(tokenData.access_token)) {
        const storageError = new Error("Authentication session could not be stored");
        storageError.code = "INVALID_AUTH_RESPONSE";
        throw storageError;
      }
      tokenStored = true;
      const { data: user } = await getMe();
      if (user?.is_active !== true) {
        clearSession();
        setError("This account is inactive. Contact your SYS administrator for access.");
        return;
      }
      const destination = roleLandingPath(user.role);
      if (!destination) {
        clearSession();
        setError("This account does not have a supported SYS role.");
        return;
      }
      await router.replace(destination);
    } catch (loginError) {
      clearSession();
      if (tokenStored && loginError?.response?.status === 401) {
        await router.replace("/login?reason=expired");
        return;
      }
      setError(
        loginError?.code === "INVALID_AUTH_RESPONSE"
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
        <meta name="description" content="Secure login for SYS students, faculty and administrators." />
      </Head>

      <main className={styles.authPage}>
        <section className={styles.identityPanel} aria-labelledby="sys-login-intro">
          <Link href="/" className={styles.homeLink} aria-label="Return to SYS homepage">
            <Image
              src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
              alt="SYS – Strengthen Your Skills"
              width={520}
              height={144}
              className={styles.identityLogo}
              preload
            />
          </Link>
          <div className={styles.identityCopy}>
            <p className={styles.eyebrow}>AI-powered learning platform</p>
            <h1 id="sys-login-intro">One secure entry to your SYS workspace.</h1>
            <p>
              Students, faculty and administrators use the same login. SYS opens the
              workspace assigned to your account after verification.
            </p>
            <ul className={styles.trustList}>
              <li><CheckCircleIcon aria-hidden="true" /> Role-aware access</li>
              <li><ShieldCheckIcon aria-hidden="true" /> Protected account session</li>
              <li><LockClosedIcon aria-hidden="true" /> No public account creation</li>
            </ul>
          </div>
          <p className={styles.identityFootnote}>Strengthen Your Skills. Shape Your Future.</p>
        </section>

        <section className={styles.formPanel} aria-labelledby="login-title">
          <div className={styles.mobileBrand}>
            <Link href="/" aria-label="Return to SYS homepage">
              <Image
                src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
                alt="SYS – Strengthen Your Skills"
                width={520}
                height={144}
                className={styles.mobileLogo}
              />
            </Link>
          </div>

          <div className={styles.formCard}>
            <div className={styles.formHeading}>
              <p className={styles.formEyebrow}>Welcome to SYS</p>
              <h2 id="login-title">Log in to continue</h2>
              <p>Use the credentials issued by your SYS administrator.</p>
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
                  <label htmlFor={identifierId}>Registered email address</label>
                  <input
                    id={identifierId}
                    name="username"
                    type="email"
                    autoComplete="username"
                    value={identifier}
                    onChange={(event) => setIdentifier(event.target.value)}
                    placeholder="Enter your registered email address"
                    required
                    disabled={submitting}
                  />
                  <p>Use the email address registered by your SYS administrator. Roll numbers and employee codes are not supported for login yet.</p>
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

            <p className={styles.accessNote}>
              Need access or account help? Contact your institution’s SYS administrator.
            </p>
          </div>
        </section>
      </main>
    </>
  );
}

LoginPage.getLayout = (page) => page;
