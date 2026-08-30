import MasterRecordCreatePage from "../../../components/admin/MasterRecordCreatePage";

export default function NewStudentPage() {
  return <MasterRecordCreatePage kind="student" />;
}

NewStudentPage.getLayout = (page) => page;
