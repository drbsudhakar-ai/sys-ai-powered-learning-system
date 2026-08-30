import Image from "next/image";
import Link from "next/link";
import {
  CheckCircleIcon,
  LockClosedIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import AuthFooter from "./AuthFooter";
import styles from "./Auth.module.css";

function AuthBrand({ compact = false }) {
  return (
    <span className={`${styles.authBrand} ${compact ? styles.authBrandCompact : ""}`}>
      <span className={styles.authBrandMark}>
        <Image
          src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
          alt=""
          width={52}
          height={52}
          loading="eager"
        />
      </span>
      <span className={styles.authBrandCopy}>
        <strong>SYS — Strengthen Your Skills</strong>
        <small>AI-Powered Learning Platform</small>
      </span>
    </span>
  );
}

export default function AuthShell({ children, introTitle, introDescription }) {
  return (
    <main className={styles.authPage}>
      <section className={styles.identityPanel} aria-labelledby="sys-auth-intro">
        <Link href="/" className={styles.homeLink} aria-label="Return to SYS homepage">
          <AuthBrand />
        </Link>
        <div className={styles.identityCopy}>
          <p className={styles.eyebrow}>AI-powered learning platform</p>
          <h1 id="sys-auth-intro">{introTitle}</h1>
          <p>{introDescription}</p>
          <ul className={styles.trustList}>
            <li><CheckCircleIcon aria-hidden="true" /> One role-aware SYS account</li>
            <li><ShieldCheckIcon aria-hidden="true" /> Verified account ownership</li>
            <li><LockClosedIcon aria-hidden="true" /> Controlled institutional registration</li>
          </ul>
        </div>
        <p className={styles.identityFootnote}>Strengthen Your Skills. Shape Your Future.</p>
      </section>

      <section className={styles.formPanel}>
        <div className={styles.mobileBrand}>
          <Link href="/" aria-label="Return to SYS homepage">
            <AuthBrand compact />
          </Link>
        </div>
        <div className={styles.formStack}>
          <div className={styles.formCard}>{children}</div>
          <AuthFooter />
        </div>
      </section>
    </main>
  );
}
