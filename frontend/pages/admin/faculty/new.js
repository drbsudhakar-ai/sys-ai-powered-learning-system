import MasterRecordCreatePage from "../../../components/admin/MasterRecordCreatePage";

export default function NewFacultyPage() {
  return <MasterRecordCreatePage kind="faculty" />;
}

NewFacultyPage.getLayout = (page) => page;
