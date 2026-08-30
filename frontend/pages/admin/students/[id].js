import MasterRecordProfilePage from "../../../components/admin/MasterRecordProfilePage";

export default function StudentDetailsPage() {
  return <MasterRecordProfilePage kind="student" />;
}

StudentDetailsPage.getLayout = (page) => page;
