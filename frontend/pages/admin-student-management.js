/**
 * Admin Student Management Page for SYS AI Lecturer System
 * --------------------------------------------------------
 * This page allows administrators to manage student registrations and progress.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Student list with details (name, roll number, enrolled courses, progress)
 *  - Filters for course type and progress status
 *  - Actions: View Profile, Assign Remedial Classes, Send Notifications
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for interactive elements
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";

export default function AdminStudentManagementPage() {
  // Example state for demo purposes
  const [students] = useState([
    { name: "Alice", rollNumber: "2026A01", course: "Mathematics", progress: 85 },
    { name: "Bob", rollNumber: "2026B02", course: "Physics", progress: 60 },
    { name: "Charlie", rollNumber: "2026C03", course: "English", progress: 40 }
  ]);

  return (
    <Layout>
    <div className="min-h-screen bg-sys-white flex flex-col">


      {/* =========================
          Student Management Content
          ========================= */}
      <main className="flex-1 p-6">
        
        {/* Filters */}
        <section className="mb-6 flex gap-4 items-center">
          <select aria-label="Filter by Course" className="input-field">
            <option>All Courses</option>
            <option>Mathematics</option>
            <option>Physics</option>
            <option>English</option>
          </select>
          <select aria-label="Filter by Progress" className="input-field">
            <option>All Status</option>
            <option>Completed</option>
            <option>In Progress</option>
            <option>Pending</option>
          </select>
        </section>

        {/* Student List */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Registered Students</h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b">
                <th>Name</th>
                <th>Roll Number</th>
                <th>Course</th>
                <th>Progress</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student, index) => (
                <tr key={index} className="border-b">
                  <td>{student.name}</td>
                  <td>{student.rollNumber}</td>
                  <td>{student.course}</td>
                  <td>
                    <div className="sys-progress" style={{ width: `${student.progress}%` }}></div>
                    <p className="text-xs mt-1">{student.progress}%</p>
                  </td>
                  <td>
                    <button className="btn-secondary mx-1" aria-label="View Profile">View</button>
                    <button className="btn-secondary mx-1" aria-label="Assign Remedial Class">Remedial</button>
                    <button className="btn-secondary mx-1" aria-label="Send Notification">Notify</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>

      {/* =========================
          Footer Section
          ========================= */}

    </div>
    </Layout>
  );
}
