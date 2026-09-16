import Head from "next/head";
import { useRouter } from "next/router";
import AdminShell from "../../../../components/admin/AdminShell";
import BrandedState from "../../../../components/admin/BrandedState";
import useAdminAccess from "../../../../components/admin/useAdminAccess";
import CourseKnowledgeStudio from "../../../../components/knowledge/CourseKnowledgeStudio";

export default function AdminCourseKnowledgeStudioPage() {
  const router = useRouter(); const access = useAdminAccess(); const courseId = router.query.id;
  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing Course Knowledge Studio." />;
  if (access.status === "error") return <BrandedState type="error" title="Knowledge Studio unavailable" message={access.error} />;
  if (access.status !== "ready") return null;
  return <><Head><title>Course Knowledge Studio | SYS</title></Head><AdminShell user={access.user} unreadNotifications={0} breadcrumb="Academic Management" pageTitle="Course Knowledge Studio" scopeLabel="Professor-grade teaching foundation"><CourseKnowledgeStudio courseId={courseId} canActivate backHref={`/admin/courses/${courseId}`} /></AdminShell></>;
}

AdminCourseKnowledgeStudioPage.getLayout = (page) => page;
