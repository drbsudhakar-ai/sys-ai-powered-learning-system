import Head from "next/head";
import { useRouter } from "next/router";
import AdminShell from "../../../../components/admin/AdminShell";
import BrandedState from "../../../../components/admin/BrandedState";
import useAdminAccess from "../../../../components/admin/useAdminAccess";
import KnowledgeReviewWorkspace from "../../../../components/knowledge/KnowledgeReviewWorkspace";

export default function AdminKnowledgeReviewsPage() {
  const router = useRouter(); const access = useAdminAccess();
  if (access.status === "checking") return <BrandedState title="Verifying administrator access" message="Preparing governed knowledge reviews." />;
  if (access.status === "error") return <BrandedState type="error" title="Knowledge reviews unavailable" message={access.error} />;
  if (access.status !== "ready") return null;
  return <><Head><title>Knowledge Package Reviews | SYS</title></Head><AdminShell user={access.user} unreadNotifications={0} breadcrumb="Academic Management" pageTitle="Knowledge Package Reviews" scopeLabel="Independent verification"><KnowledgeReviewWorkspace courseId={router.query.id} admin /></AdminShell></>;
}
AdminKnowledgeReviewsPage.getLayout = (page) => page;
