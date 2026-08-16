import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { getMe } from "../../src/api";
import { clearSession, getToken, isAdminRole, roleLandingPath } from "../../src/auth";

export default function useAdminAccess() {
  const router = useRouter();
  const [state, setState] = useState({ status: "checking", user: null, error: "" });

  useEffect(() => {
    if (!router.isReady) return undefined;
    const controller = new AbortController();
    let active = true;

    async function authorize() {
      const token = getToken();
      if (!token) {
        await router.replace("/login?reason=unauthorized");
        return;
      }
      try {
        const response = await getMe({ signal: controller.signal });
        if (!active) return;
        const account = response?.data;
        if (!account || typeof account !== "object" || typeof account.role !== "string" || typeof account.is_active !== "boolean") {
          setState({ status: "error", user: null, error: "SYS received an invalid account response." });
          return;
        }
        if (!account.is_active) {
          clearSession();
          await router.replace("/login?reason=unauthorized");
          return;
        }
        if (!isAdminRole(account.role)) {
          await router.replace(roleLandingPath(account.role) || "/login?reason=unauthorized");
          return;
        }
        setState({ status: "ready", user: account, error: "" });
      } catch (error) {
        if (!active || error?.code === "ERR_CANCELED") return;
        if (error?.response?.status === 401) {
          clearSession();
          await router.replace("/login?reason=expired");
          return;
        }
        if (error?.response?.status === 403) {
          await router.replace("/login?reason=unauthorized");
          return;
        }
        setState({
          status: "error",
          user: null,
          error: "SYS could not verify administrator access. Check the API service and try again.",
        });
      }
    }

    authorize();
    return () => {
      active = false;
      controller.abort();
    };
  }, [router, router.isReady]);

  return state;
}
