import AdminShell from "./AdminShell";
import BrandedState from "./BrandedState";
import useAdminAccess from "./useAdminAccess";
import SyllabusReviewWorkspace from "../syllabus/SyllabusReviewWorkspace";
export default function CourseSyllabusWorkspace({ page = "structure" }) {
  const access = useAdminAccess();
  if (access.status === "error") return <BrandedState type="error" title="Unable to verify access" message={access.error} actionHref="/admin/courses" actionLabel="Back to Course Master" />;
  if (access.status !== "ready") return <BrandedState title="Syllabus review" message="Checking administrator access…" />;
  return <AdminShell user={access.user} breadcrumb="Academic Management" pageTitle="Syllabus Management" scopeLabel="Course governance"><SyllabusReviewWorkspace page={page} /></AdminShell>;
}
