import Head from "next/head";
import { useRouter } from "next/router";
import { useEffect } from "react";
import { getMe } from "../src/api";
import { clearSession, roleLandingPath } from "../src/auth";

export default function DashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    let active = true;

    getMe()
      .then(({ data }) => {
        if (active) router.replace(roleLandingPath(data?.role));
      })
      .catch(() => {
        clearSession();
        if (active) router.replace("/login?reason=session-expired");
      });

    return () => {
      active = false;
    };
  }, [router]);

  return (
    <>
      <Head>
        <title>Opening your dashboard | SYS</title>
      </Head>
      <main
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          color: "#0b326f",
        }}
      >
        <p>Opening your authorized SYS workspace…</p>
      </main>
    </>
  );
}

DashboardRedirect.getLayout = (page) => page;
