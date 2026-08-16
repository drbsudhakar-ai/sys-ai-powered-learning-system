import Head from "next/head";

import LandingPage from "../components/landing/LandingPage";

function Home() {
  return (
    <>
      <Head>
        <title>SYS – Strengthen Your Skills</title>
        <meta
          name="description"
          content="SYS connects learning, practice, assessment, performance analysis, remedial learning and student support in one AI-powered learning journey."
        />
        <link
          rel="icon"
          href="/branding/sys-v2/icons/favicon.ico"
        />
        <link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" />
      </Head>
      <LandingPage />
    </>
  );
}

// This page has a purpose-built shell. Other routes keep the shared layout.
Home.getLayout = (page) => page;

export default Home;
