import MasterWorkspace from "../../../components/admin/MasterWorkspace";

export default function AdminStudentsPage() {
  return <MasterWorkspace kind="student" />;
}

AdminStudentsPage.getLayout = (page) => page;
