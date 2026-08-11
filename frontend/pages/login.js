/**
 * Student Login Page for SYS AI Lecturer System
 * ---------------------------------------------
 * This page allows registered students to log in using:
 *  - Email
 *  - Password
 * 
 * Branding:
 *  - SYS Logo + Tagline at the top
 *  - Theme colors from SYS Brand Kit CSS
 *  - Developer credit line in footer
 * 
 * Accessibility:
 *  - ARIA labels for form inputs
 *  - Semantic HTML structure
 */

import { useState } from "react";
import Layout from "../components/Layout";
import { loginUser } from "../api";

export default function LoginPage() {
  // Local state for form fields
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [message, setMessage] = useState(null);

  // Handle input changes
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    try {
      const res = await loginUser(formData);
      localStorage.setItem("token", res.data.access_token);
      setMessage({ type: "success", text: "Login successful! Redirecting..." });
      window.location.href = "/dashboard"; // redirect after login
    } catch (err) {
      setMessage({ type: "error", text: "Login failed. Check your credentials." });
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-sys-white flex flex-col items-center justify-center">
        
        {/* =========================
            Header Section
            ========================= */}
        <header className="text-center mb-6">
          <div className="sys-logo">SYS – Strengthen Your Skills</div>
          <div className="sys-tagline">Shape Your Future</div>
        </header>

        {/* =========================
            Login Form
            ========================= */}
        <main className="sys-card w-full max-w-md">
          <h2 className="text-xl font-semibold text-sys-blue mb-4 text-center">
            Student Login
          </h2>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Email */}
            <input
              type="email"
              name="username"
              placeholder="Email"
              value={formData.username}
              onChange={handleChange}
              aria-label="Email"
              className="input-field"
              required
            />

            {/* Password */}
            <input
              type="password"
              name="password"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
              aria-label="Password"
              className="input-field"
              required
            />

            {/* Submit Button */}
            <button type="submit" className="btn-primary">
              Login
            </button>
          </form>

          {/* Feedback Messages */}
          {message && (
            <p className={message.type === "error" ? "error" : "success"}>
              {message.text}
            </p>
          )}
        </main>

        {/* =========================
            Footer Section
            ========================= */}
      </div>
    </Layout>
  );
}
