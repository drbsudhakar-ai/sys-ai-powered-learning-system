import Link from "next/link";
import styles from "./WorkspaceBreadcrumbs.module.css";

export default function WorkspaceBreadcrumbs({ items = [] }) {
  return <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
    <ol>{items.map((item, index) => {
      const current = index === items.length - 1;
      return <li key={`${item.label}-${index}`}>{index > 0 && <span aria-hidden="true">/</span>}{!current && item.href ? <Link href={item.href}>{item.label}</Link> : <span aria-current={current ? "page" : undefined}>{item.label}</span>}</li>;
    })}</ol>
  </nav>;
}
