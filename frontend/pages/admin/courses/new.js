import CourseRecordFormPage from "../../../components/admin/CourseRecordFormPage";

export default function NewAdminCoursePage() {
  return <CourseRecordFormPage mode="create" />;
}

NewAdminCoursePage.getLayout = (page) => page;
