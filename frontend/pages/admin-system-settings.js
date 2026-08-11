/**
 * Admin System Settings Page for SYS AI Lecturer System
 * -----------------------------------------------------
 * This page allows administrators to configure system-wide settings.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Panels for:
 *      • User & Role Management
 *      • Security Settings
 *      • Data Management
 *      • System Preferences
 *  - Quick action buttons (Save, Restore Defaults, Export Config)
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for interactive elements
 *  - Semantic HTML structure
 */

import Layout from "../components/Layout";
export default function AdminSystemSettingsPage() {
    return (
      <Layout>
      <div className="min-h-screen bg-sys-white flex flex-col">
        
      
  
        {/* =========================
            Settings Content
            ========================= */}
        <main className="flex-1 p-6 grid gap-6 md:grid-cols-2">
          
          {/* User & Role Management */}
          <section className="sys-card">
            <h3 className="text-lg font-bold text-sys-blue mb-4">User & Role Management</h3>
            <ul className="list-disc list-inside text-sm mb-4">
              <li>Manage roles (Student, Admin)</li>
              <li>Add/remove admin accounts</li>
              <li>Reset student passwords</li>
            </ul>
            <div className="flex gap-2">
              <button className="btn-primary" aria-label="Add Admin">Add Admin</button>
              <button className="btn-secondary" aria-label="Reset Password">Reset Password</button>
            </div>
          </section>
  
          {/* Security Settings */}
          <section className="sys-card">
            <h3 className="text-lg font-bold text-sys-blue mb-4">Security Settings</h3>
            <ul className="list-disc list-inside text-sm mb-4">
              <li>Enable/disable facial recognition</li>
              <li>Configure login policies (password strength, 2FA)</li>
              <li>View audit logs</li>
            </ul>
            <div className="flex gap-2">
              <button className="btn-primary" aria-label="Enable 2FA">Enable 2FA</button>
              <button className="btn-secondary" aria-label="View Logs">View Logs</button>
            </div>
          </section>
  
          {/* Data Management */}
          <section className="sys-card">
            <h3 className="text-lg font-bold text-sys-blue mb-4">Data Management</h3>
            <ul className="list-disc list-inside text-sm mb-4">
              <li>Backup/export student/course data</li>
              <li>Import roll numbers from Excel</li>
              <li>Clear cache or archived data</li>
            </ul>
            <div className="flex gap-2">
              <button className="btn-primary" aria-label="Backup Data">Backup</button>
              <button className="btn-secondary" aria-label="Import Excel">Import Excel</button>
            </div>
          </section>
  
          {/* System Preferences */}
          <section className="sys-card">
            <h3 className="text-lg font-bold text-sys-blue mb-4">System Preferences</h3>
            <ul className="list-disc list-inside text-sm mb-4">
              <li>Language options (English ↔ Telugu)</li>
              <li>Notification settings (email, in-app)</li>
              <li>Theme customization (light/dark mode)</li>
            </ul>
            <div className="flex gap-2">
              <button className="btn-primary" aria-label="Change Language">Change Language</button>
              <button className="btn-secondary" aria-label="Toggle Theme">Toggle Theme</button>
            </div>
          </section>
        </main>
  
        {/* =========================
            Quick Actions
            ========================= */}
        <section className="p-6 text-center border-t border-gray-200">
          <button className="btn-primary mx-2" aria-label="Save Settings">Save Settings</button>
          <button className="btn-secondary mx-2" aria-label="Restore Defaults">Restore Defaults</button>
          <button className="btn-secondary mx-2" aria-label="Export Configuration">Export Config</button>
        </section>
  
        {/* =========================
            Footer Section
            ========================= */}
       
      </div>
      </Layout>
    );
  }
  