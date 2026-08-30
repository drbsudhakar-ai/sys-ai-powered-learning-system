import MasterRecordProfilePage from "../../../components/admin/MasterRecordProfilePage";

export default function FacultyDetailsPage() {
  return <MasterRecordProfilePage kind="faculty" />;
}

FacultyDetailsPage.getLayout = (page) => page;
