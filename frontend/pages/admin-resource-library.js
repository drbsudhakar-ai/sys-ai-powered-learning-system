/**
 * Admin Resource Library Page for SYS AI Lecturer System
 * ------------------------------------------------------
 * This page allows administrators to manage uploaded course resources.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Upload section (drag-and-drop for PDF, Word, images, videos)
 *  - Resource list with file details and actions
 *  - Filters and search bar
 *  - Quick actions (Upload New Resource, Link Resource to Course, Export Resource List)
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for interactive elements
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";

export default function AdminResourceLibraryPage() {
  // Example state for demo purposes
  const [resources] = useState([
    { name: "Math Notes.pdf", type: "PDF", course: "Mathematics", date: "Aug 1, 2026", status: "Completed" },
    { name: "Physics Lecture.mp4", type: "Video", course: "Physics", date: "Aug 3, 2026", status: "Completed" },
    { name: "English Essay.docx", type: "Word", course: "English", date: "Aug 5, 2026", status: "Completed" }
  ]);

  return (
    <Layout>  
    <div className="min-h-screen bg-sys-white flex flex-col">
      


      {/* =========================
          Resource Library Content
          ========================= */}
      <main className="flex-1 p-6">
        
        {/* Upload Section */}
        <section className="sys-card mb-6">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Upload Resources</h3>
          <div className="border-2 border-dashed border-sys-blue p-6 text-center rounded-lg">
            <p className="text-sm text-sys-gray">Drag & drop files here or click to upload</p>
            <p className="text-xs text-sys-orange mt-2">Supported: PDF, Word, Images, Videos</p>
          </div>
        </section>

        {/* Filters & Search */}
        <section className="mb-6 flex gap-4 items-center">
          <input
            type="text"
            placeholder="Search resources..."
            aria-label="Search Resources"
            className="input-field flex-1"
          />
          <select className="input-field">
            <option>All Courses</option>
            <option>Mathematics</option>
            <option>Physics</option>
            <option>English</option>
          </select>
          <select className="input-field">
            <option>All Types</option>
            <option>PDF</option>
            <option>Word</option>
            <option>Image</option>
            <option>Video</option>
          </select>
        </section>

        {/* Resource List */}
        <section className="sys-card">
          <h3 className="text-lg font-bold text-sys-blue mb-4">Resource List</h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b">
                <th>File Name</th>
                <th>Type</th>
                <th>Course</th>
                <th>Upload Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((res, index) => (
                <tr key={index} className="border-b">
                  <td>{res.name}</td>
                  <td>{res.type}</td>
                  <td>{res.course}</td>
                  <td>{res.date}</td>
                  <td>{res.status}</td>
                  <td>
                    <button className="btn-secondary mx-1" aria-label="Preview Resource">Preview</button>
                    <button className="btn-secondary mx-1" aria-label="Edit Resource">Edit</button>
                    <button className="btn-secondary mx-1" aria-label="Delete Resource">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Quick Actions */}
        <section className="mt-6 text-center">
          <button className="btn-primary mx-2" aria-label="Upload New Resource">Upload New Resource</button>
          <button className="btn-secondary mx-2" aria-label="Link Resource to Course">Link Resource to Course</button>
          <button className="btn-secondary mx-2" aria-label="Export Resource List">Export Resource List</button>
        </section>
      </main>

    
    </div>
    </Layout>
  );
}
