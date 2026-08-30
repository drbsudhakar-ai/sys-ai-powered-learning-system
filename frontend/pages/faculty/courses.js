import { useRouter } from "next/router";
import { useEffect } from "react";
import { getRoleDashboard } from "../../src/api";

export default function AssignedCoursesRedirect(){
  const router=useRouter();
  useEffect(()=>{getRoleDashboard().then(({data})=>{
    const destination=data?.courses?.length?"/faculty/coordinator-courses":data?.subjects?.length?"/faculty/subject-expert-courses":"/faculty-dashboard";
    router.replace(destination);
  }).catch(()=>router.replace("/faculty-dashboard"));},[router]);
  return <p style={{padding:32}}>Opening your assigned-course workspace…</p>;
}
