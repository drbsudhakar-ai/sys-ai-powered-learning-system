import styles from "./Auth.module.css";

export default function AuthFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className={styles.authFooter}>
      <p>© {year} SYS — Strengthen Your Skills. All rights reserved.</p>
      <p>Shape Your Successful Future.</p>
      <p>AI-Powered Learning Platform</p>
    </footer>
  );
}
