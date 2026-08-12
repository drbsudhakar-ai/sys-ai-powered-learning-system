import { useEffect } from "react";
import { useRouter } from "next/router";

/** Legacy stub → real Admin Student Management (P0-008). */
export default function AdminStudentManagementRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/students");
  }, [router]);
  return <p className="sys-card mx-auto mt-8">Redirecting to Students…</p>;
}
