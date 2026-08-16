import MasterWorkspace from "../../../components/admin/MasterWorkspace";

export default function AdminFacultyPage() {
  return <MasterWorkspace kind="faculty" />;
}

AdminFacultyPage.getLayout = (page) => page;
