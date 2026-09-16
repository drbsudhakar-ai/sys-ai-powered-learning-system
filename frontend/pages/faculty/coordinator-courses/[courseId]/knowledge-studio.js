import Head from "next/head";
import { useRouter } from "next/router";
import BrandedState from "../../../../components/admin/BrandedState";
import useAdminAccess from "../../../../components/admin/useAdminAccess";
import RoleWorkspaceShell from "../../../../components/auth/RoleWorkspaceShell";
import CourseKnowledgeStudio from "../../../../components/knowledge/CourseKnowledgeStudio";

export default function CoordinatorCourseKnowledgeStudioPage() {
  const router = useRouter(); const access = useAdminAccess({ allowFaculty: true }); const courseId = router.query.courseId;
  if (access.status === "checking") return <BrandedState title="Verifying course responsibility" message="Preparing Course Knowledge Studio." />;
  if (access.status === "error") return <BrandedState type="error" title="Knowledge Studio unavailable" message={access.error} />;
  if (access.status !== "ready") return null;
  return <><Head><title>Course Knowledge Studio | SYS</title></Head><RoleWorkspaceShell role="faculty" identity={access.user}><CourseKnowledgeStudio courseId={courseId} canActivate={false} backHref="/faculty/coordinator-courses" /></RoleWorkspaceShell></>;
}

CoordinatorCourseKnowledgeStudioPage.getLayout = (page) => page;
