/**
 * Forgot Password Page for SYS AI Lecturer System
 * -----------------------------------------------
 * This page allows students to reset their password if forgotten.
 * Features:
 *  - SYS Logo + Tagline at the top
 *  - Email input for password reset
 *  - Submit button to request reset link
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for form inputs
 *  - Semantic HTML structure
 */

import { useState } from 'react';
import Layout from "../components/Layout";
export default function ForgotPasswordPage() {
  // Local state for email field
  const [email, setEmail] = useState('');

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Connect to backend API (FastAPI /auth/forgot-password)
    console.log('Password reset requested for:', email);
  };

  return (
    <Layout>      
    <div className="min-h-screen bg-sys-white flex flex-col items-center justify-center">
      
   

      {/* =========================
          Forgot Password Form
          ========================= */}
      <main className="sys-card w-full max-w-md">
        <h2 className="text-xl font-semibold text-sys-blue mb-4 text-center">
          Forgot Password
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
            Send Reset Link
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
