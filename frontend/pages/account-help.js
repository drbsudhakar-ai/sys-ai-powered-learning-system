import Head from "next/head";
import Link from "next/link";
import { ArrowLeftIcon, IdentificationIcon, KeyIcon, UserCircleIcon } from "@heroicons/react/24/outline";
import AuthShell from "../components/auth/AuthShell";
import styles from "../components/auth/Auth.module.css";


export default function AccountHelpPage() {
  return (
    <>
      <Head>
        <title>Account help | SYS</title>
        <meta name="description" content="Guidance for SYS registration, login and account recovery." />
      </Head>
      <AuthShell
        introTitle="Clear help for secure SYS account access."
        introDescription="Your institution controls student and faculty master records. SYS protects those records with verified activation, recovery, and role-aware access."
      >
        <div className={styles.formHeading}>
          <p className={styles.formEyebrow}>Account guidance</p>
          <h2>Need account help?</h2>
          <p>Choose the guidance that matches where you are in the account process.</p>
        </div>

        <div className={styles.helpCards}>
          <article>
            <IdentificationIcon aria-hidden="true" />
            <div><h3>Registration does not verify</h3><p>Confirm the roll number or employee code and the role selected. If your preloaded contact is missing or outdated, ask your SYS administrator to correct the institutional record.</p></div>
          </article>
          <article>
            <UserCircleIcon aria-hidden="true" />
            <div><h3>Login is not accepted</h3><p>Use a verified email, unique personal mobile with country code, roll number, or employee code. Disabled and academically inactive accounts require administrator assistance.</p></div>
          </article>
          <article>
            <KeyIcon aria-hidden="true" />
            <div><h3>No recovery code arrives</h3><p>Choose a contact method already verified on your active account. Delivery requires your institution’s configured email or SMS provider; SYS never displays recovery codes.</p></div>
          </article>
        </div>

        <nav className={styles.authLinks} aria-label="Account help actions">
          <Link href="/register">Register your account</Link>
          <Link href="/forgot-password">Forgot password?</Link>
        </nav>
        <p className={styles.backLink}><ArrowLeftIcon aria-hidden="true" /><Link href="/login">Back to login</Link></p>
      </AuthShell>
    </>
  );
}

AccountHelpPage.getLayout = (page) => page;
