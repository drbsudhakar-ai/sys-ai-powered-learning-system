import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { getMe, getCourses } from "../api";

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userRes = await getMe();
        setUser(userRes.data);

        const coursesRes = await getCourses();
        setCourses(coursesRes.data);
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <p>Loading dashboard...</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-sys-white flex flex-col items-center">
        
        {/* =========================
            Header Section
            ========================= */}
        <header className="text-center py-6 border-b border-gray-200 w-full">
          <div className="sys-logo">SYS – Strengthen Your Skills</div>
          <div className="sys-tagline">Shape Your Future</div>
        </header>

        {/* =========================
            Dashboard Content
            ========================= */}
        <main className="w-full max-w-3xl p-6">
          {/* Greeting + Photo */}
          <div className="flex items-center gap-4 mb-6">
            {user?.photo_url ? (
              <img
                src={user.photo_url}
                alt={`${user.name}'s profile`}
                className="w-20 h-20 rounded-full border-2 border-sys-blue"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gray-300 flex items-center justify-center text-gray-600">
                No Photo
              </div>
            )}
            <h2 className="text-xl font-semibold text-sys-blue">
              Welcome back, {user?.name}!
            </h2>
          </div>

          {/* Course Overview */}
          <section className="mb-8">
            <h3 className="text-lg font-bold text-sys-gray mb-2">Your Courses</h3>
            {courses.length > 0 ? (
              <ul className="space-y-4">
                {courses.map((course) => (
                  <li key={course.id} className="sys-card p-4">
                    <p className="font-semibold">{course.title}</p>
                    {/* Progress bar */}
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div
                        className="bg-sys-blue h-2 rounded-full"
                        style={{ width: `${course.progress || 0}%` }}
                        aria-label={`Course progress ${course.progress || 0}%`}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Progress: {course.progress || 0}%
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No courses enrolled yet.</p>
            )}
          </section>

          {/* Upcoming Assessments */}
          <section>
            <h3 className="text-lg font-bold text-sys-gray mb-2">Upcoming Assessments</h3>
            {user?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside text-sm">
                {user.assessments.map((a) => (
                  <li key={a.id}>
                    {a.title} – Due {new Date(a.due_date).toLocaleDateString()}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No upcoming assessments.</p>
            )}
          </section>
        </main>

        {/* =========================
            Footer Section
            ========================= */}
        <footer className="py-4 text-sm text-sys-gray text-center border-t border-gray-200 w-full">
          © 2026 SYS AI Lecturer System. Developed by Dr. B Sudhakar. All rights reserved.
        </footer>
      </div>
    </Layout>
  );
}
