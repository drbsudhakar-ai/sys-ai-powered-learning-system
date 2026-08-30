import AdminShell from "./AdminShell";
import Link from "next/link";
import { useRouter } from "next/router";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import SyllabusReviewWorkspace from "../syllabus/SyllabusReviewWorkspace";
export default function CourseSyllabusWorkspace({ page = "structure" }) {
  const router = useRouter();
  const access = useAdminAccess();
  if (access.status === "error") return <BrandedState type="error" title="Unable to verify access" message={access.error} actionHref="/admin/courses" actionLabel="Back to Course Master" />;
  if (access.status !== "ready") return <BrandedState title="Syllabus review" message="Checking administrator access…" />;
  return <AdminShell user={access.user} breadcrumb="Academic Management" pageTitle="Syllabus Management" scopeLabel="Course governance"><Link href={`/admin/courses/${router.query.id}/weightages`} className="sys-button">Manage academic weightages</Link><SyllabusReviewWorkspace page={page} /></AdminShell>;
}
