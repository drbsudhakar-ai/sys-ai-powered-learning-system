import Head from "next/head";
import BrandedState from "../../components/admin/BrandedState";
import useAdminAccess from "../../components/admin/useAdminAccess";
import RoleWorkspaceShell from "../../components/auth/RoleWorkspaceShell";
import KnowledgeReviewWorkspace from "../../components/knowledge/KnowledgeReviewWorkspace";

export default function FacultyAcademicReviewsPage() {
  const access = useAdminAccess({ allowFaculty: true });
  if (access.status === "checking") return <BrandedState title="Verifying reviewer responsibility" message="Preparing assigned academic content reviews." />;
  if (access.status === "error") return <BrandedState type="error" title="Academic reviews unavailable" message={access.error} />;
  if (access.status !== "ready") return null;
  return <><Head><title>My Academic Content Reviews | SYS</title></Head><RoleWorkspaceShell role="faculty" identity={access.user}><KnowledgeReviewWorkspace /></RoleWorkspaceShell></>;
}
FacultyAcademicReviewsPage.getLayout = (page) => page;
