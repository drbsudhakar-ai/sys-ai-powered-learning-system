/**
 * Admin Assessment Management Page for SYS AI Lecturer System
 * -----------------------------------------------------------
 * This page allows administrators to create, configure, and monitor assessments.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Assessment creation form (title, description, duration, difficulty, course linkage)
 *  - Upload question bank (MCQs, short answers)
 *  - Assessment library with status indicators
 *  - Student performance tracking (average score, completion rate, time taken)
 *  - Quick actions (Create Assessment, Upload Question Bank, View Results)
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for interactive elements
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";
export default function AdminAssessmentManagementPage() {
  // Example state for demo purposes
  const [assessments] = useState([
    { title: "Math Unit Test", status: "Active", avgScore: 75, completionRate: "80%" },
    { title: "Physics Quiz", status: "Scheduled", avgScore: null, completionRate: null },
    { title: "English Grand Test", status: "Completed", avgScore: 88, completionRate: "95%" }
  ]);

  return (
    <Layout>
    <div className="min-h-screen bg-sys-white flex flex-col">
      
     
      {/* =========================
          Assessment Management Content
          ========================= */}
      <main className="flex-1 p-6 grid gap-6 md:grid-cols-2">
        
        {/* Assessment Creation Form */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Create New Assessment</h3>
          <form className="flex flex-col gap-3">
            <input type="text" placeholder="Title" aria-label="Assessment Title" className="input-field" required />
            <textarea placeholder="Description" aria-label="Assessment Description" className="input-field"></textarea>
            <input type="number" placeholder="Duration (minutes)" aria-label="Assessment Duration" className="input-field" />
            <select aria-label="Difficulty Level" className="input-field">
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </select>
            <select aria-label="Course Linkage" className="input-field">
              <option>Mathematics</option>
              <option>Physics</option>
              <option>English</option>
            </select>
            <button type="submit" className="btn-primary">Create Assessment</button>
          </form>
        </section>

        {/* Assessment Library */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Assessment Library</h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b">
                <th>Title</th>
                <th>Status</th>
                <th>Avg Score</th>
                <th>Completion Rate</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((assess, index) => (
                <tr key={index} className="border-b">
                  <td>{assess.title}</td>
                  <td>{assess.status}</td>
                  <td>{assess.avgScore !== null ? `${assess.avgScore}%` : "-"}</td>
                  <td>{assess.completionRate || "-"}</td>
                  <td>
                    <button className="btn-secondary mx-1" aria-label="Edit Assessment">Edit</button>
                    <button className="btn-secondary mx-1" aria-label="Delete Assessment">Delete</button>
                    <button className="btn-secondary mx-1" aria-label="View Results">View Results</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>

      {/* =========================
          Quick Actions
          ========================= */}
      <section className="p-6 text-center border-t border-gray-200">
        <button className="btn-primary mx-2" aria-label="Upload Question Bank">Upload Question Bank</button>
        <button className="btn-secondary mx-2" aria-label="Export Results">Export Results</button>
      </section>

      {/* =========================
          Footer Section
          ========================= */}
      
    </div>
    </Layout>
  );
}
