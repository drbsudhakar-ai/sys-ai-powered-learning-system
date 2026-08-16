import Image from "next/image";
import Link from "next/link";
import {
  CheckCircleIcon,
  LockClosedIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import AuthFooter from "./AuthFooter";
import styles from "./Auth.module.css";

export default function AuthShell({ children, introTitle, introDescription }) {
  return (
    <main className={styles.authPage}>
      <section className={styles.identityPanel} aria-labelledby="sys-auth-intro">
        <Link href="/" className={styles.homeLink} aria-label="Return to SYS homepage">
          <Image
            src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
            alt="SYS – Strengthen Your Skills"
            width={520}
            height={144}
            className={styles.identityLogo}
            loading="eager"
          />
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
            <Image
              src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
              alt="SYS – Strengthen Your Skills"
              width={520}
              height={144}
              className={styles.mobileLogo}
              loading="eager"
            />
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
