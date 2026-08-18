import { useEffect, useState } from "react";
import SYSHeader from "./layout/SYSHeader";
import SYSFooter from "./layout/SYSFooter";
import { getMe } from "../src/api";
import { getToken } from "../src/auth";

export default function Layout({ children }) {
  const [session, setSession] = useState({ status: "checking", user: null });

  useEffect(() => {
    let active = true;

    async function resolveSession() {
      if (!getToken()) {
        if (active) setSession({ status: "anonymous", user: null });
        return;
      }

      try {
        const response = await getMe();
        if (active) setSession({ status: "authenticated", user: response.data || null });
      } catch {
        if (active) setSession({ status: "anonymous", user: null });
      }
    }

    resolveSession();
    return () => { active = false; };
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <SYSHeader session={session} />
      <main className="flex-grow">{children}</main>
      <SYSFooter session={session} />
    </div>
  );
}
