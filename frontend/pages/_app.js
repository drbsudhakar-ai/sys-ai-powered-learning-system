/**
 * Global App Wrapper
 * ------------------
 * Ensures every page automatically uses Layout.js
 * and imports SYS brand styles globally.
 */
import Layout from "../components/Layout";

import '../styles/globals.css';

export default function MyApp({ Component, pageProps }) {
  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}
