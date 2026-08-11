/**
 * Admin Dashboard Page for SYS AI Lecturer System
 * -----------------------------------------------
 * This page serves as the main hub for administrators.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Admin panels for:
 *      • Course Management
 *      • Student Management
 *      • Assessment Management
 *  - Quick action buttons for adding/editing/removing entities
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for interactive elements
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";


export default function AdminDashboardPage() {
  // Example state for demo purposes
  const [courses] = useState(["Mathematics", "Physics", "English"]);
  const [students] = useState(["Alice", "Bob", "Charlie"]);
  const [assessments] = useState(["Math Test – Aug 15", "Physics Quiz – Aug 20"]);

  return (
    <Layout>
    <div className="min-h-screen bg-sys-white flex flex-col">
      
   

      {/* =========================
          Admin Dashboard Content
          ========================= */}
      <main className="flex-1 p-6 grid gap-6 md:grid-cols-3">
        
        {/* Course Management Panel */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Course Management</h3>
          <ul className="list-disc list-inside text-sm mb-4">
            {courses.map((course, index) => (
              <li key={index}>{course}</li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button className="btn-primary" aria-label="Add Course">Add</button>
            <button className="btn-secondary" aria-label="Edit Course">Edit</button>
            <button className="btn-secondary" aria-label="Remove Course">Remove</button>
          </div>
        </section>

        {/* Student Management Panel */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Student Management</h3>
          <ul className="list-disc list-inside text-sm mb-4">
            {students.map((student, index) => (
              <li key={index}>{student}</li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button className="btn-primary" aria-label="Add Student">Add</button>
            <button className="btn-secondary" aria-label="Edit Student">Edit</button>
            <button className="btn-secondary" aria-label="Remove Student">Remove</button>
          </div>
        </section>

        {/* Assessment Management Panel */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Assessment Management</h3>
          <ul className="list-disc list-inside text-sm mb-4">
            {assessments.map((assessment, index) => (
              <li key={index}>{assessment}</li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button className="btn-primary" aria-label="Add Assessment">Add</button>
            <button className="btn-secondary" aria-label="Edit Assessment">Edit</button>
            <button className="btn-secondary" aria-label="Remove Assessment">Remove</button>
          </div>
        </section>
      </main>

    
    </div>
    </Layout>
  );
}
