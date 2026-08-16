import Image from "next/image";
import Link from "next/link";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import styles from "./AdminDashboard.module.css";

export default function BrandedState({
  type = "loading",
  title = "Preparing your SYS workspace",
  message = "Verifying access and loading current operational data.",
  actionHref,
  actionLabel,
  compact = false,
}) {
  const Heading = compact ? "h2" : "h1";
  const content = (
    <div className={styles.stateCard} role={type === "error" ? "alert" : "status"} aria-live="polite">
      <span className={styles.stateMark}>
        {type === "error" ? (
          <ExclamationTriangleIcon aria-hidden="true" />
        ) : (
          <Image
            src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
            alt=""
            width={256}
            height={248}
            preload
          />
        )}
      </span>
      <Heading>{title}</Heading>
      <p>{message}</p>
      {actionHref && actionLabel && <Link href={actionHref}>{actionLabel}</Link>}
    </div>
  );
  return compact ? content : <main className={styles.authorizationGate}>{content}</main>;
}
