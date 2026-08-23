// frontend/pages/_document.js
import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* SYS Branding Stylesheet */}
        <link rel="stylesheet" href="/branding/sys-v2/tokens/sys-brand.css" />

        {/* SYS Favicon + Theme */}
        <link rel="icon" href="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png" />
        <meta name="theme-color" content="#0A192F" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
