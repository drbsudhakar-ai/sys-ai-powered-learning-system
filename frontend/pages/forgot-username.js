/**
 * Forgot Username Page for SYS AI Lecturer System
 * -----------------------------------------------
 * This page allows students to recover their username if forgotten.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Email input for username recovery
 *  - Submit button to request username reminder
 *  - Link back to Login page
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for form inputs
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";
export default function ForgotUsernamePage() {
  // Local state for email field
  const [email, setEmail] = useState('');

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Connect to backend API (FastAPI /auth/forgot-username)
    console.log('Username recovery requested for:', email);
  };

  return (
    <Layout>
    <div className="min-h-screen bg-sys-white flex flex-col items-center justify-center">
      

      {/* =========================
          Forgot Username Form
          ========================= */}
      <main className="sys-card w-full max-w-md">
        <h2 className="text-xl font-semibold text-sys-blue mb-4 text-center">
          Forgot Username
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Email Input */}
          <input
            type="email"
            name="email"
            placeholder="Enter your registered email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-label="Registered Email"
            className="input-field"
            required
          />

          {/* Submit Button */}
          <button type="submit" className="btn-primary">
            Send Username Reminder
          </button>
        </form>

        {/* Back to Login Link */}
        <div className="mt-4 text-sm text-center">
          <a href="/login" className="text-sys-orange hover:underline">
            Back to Login
          </a>
        </div>
      </main>

      {/* =========================
          Footer Section
          ========================= */}
   
    </div>
    </Layout>
  );
}
