import CourseRecordFormPage from "../../../../components/admin/CourseRecordFormPage";

export default function EditAdminCoursePage() {
  return <CourseRecordFormPage mode="edit" />;
}

EditAdminCoursePage.getLayout = (page) => page;
