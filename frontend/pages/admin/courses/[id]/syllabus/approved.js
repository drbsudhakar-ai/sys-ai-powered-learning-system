import CourseSyllabusWorkspace from "../../../../../components/admin/CourseSyllabusWorkspace";
export default function SyllabusPage() { return <CourseSyllabusWorkspace page="approved" />; }
SyllabusPage.getLayout = (page) => page;
