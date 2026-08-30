import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import SYSHeader from "./layout/SYSHeader";
import SYSFooter from "./layout/SYSFooter";
import RoleWorkspaceShell from "./auth/RoleWorkspaceShell";
import AdminShell from "./admin/AdminShell";
import { administratorRole } from "../src/workspaceNavigation";
import { getMe } from "../src/api";
import { getToken } from "../src/auth";

export default function Layout({ children }) {
  const router = useRouter();
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
        if (active)
          setSession({ status: "authenticated", user: response.data || null });
      } catch {
        if (active) setSession({ status: "anonymous", user: null });
      }
    }

    resolveSession();
    window.addEventListener("sys:profile-updated", resolveSession);
    return () => {
      active = false;
      window.removeEventListener("sys:profile-updated", resolveSession);
    };
  }, []);

  const role = session.user?.role;
  const roleUser =
    session.status === "authenticated" && ["student", "faculty"].includes(role);
  const publicRoutes = [
    "/",
    "/login",
    "/register",
    "/forgot-password",
    "/forgot-username",
    "/account-help",
  ];
  const roleWorkspace = roleUser && !publicRoutes.includes(router.pathname);

  // Dedicated admin pages opt out with getLayout. Shared academic pages use
  // this branch so links to lessons, reports and reviews retain the admin shell.
  if (
    session.status === "authenticated" &&
    session.user?.is_active &&
    administratorRole(role) &&
    !publicRoutes.includes(router.pathname)
  ) {
    return (
      <AdminShell
        user={session.user}
        breadcrumb="SYS Workspace"
        pageTitle="Academic workspace"
        scopeLabel="Administration"
      >
        {children}
      </AdminShell>
    );
  }

  // Faculty and student workspaces already provide persistent identity,
  // navigation and brand treatment in their sidebar. Rendering the public
  // header/footer here duplicates that workspace chrome.
  if (roleWorkspace) {
    return (
      <RoleWorkspaceShell role={role} identity={session.user}>
        <main className="flex-grow">{children}</main>
      </RoleWorkspaceShell>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SYSHeader session={session} />
      <main className="flex-grow">{children}</main>
      <SYSFooter session={session} />
    </div>
  );
}
