import { useState } from "react";
import Layout from "../components/Layout";
import CameraCapture from "../components/CameraCapture";
import { registerUser } from "../src/api";

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    fullName: "",
    rollNumber: "",
    email: "",
    password: "",
    photo: null,
  });

  const handlePhotoCapture = (photoData) => {
    setFormData({ ...formData, photo: photoData });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await registerUser({
        name: formData.fullName,
        email: formData.email,
        role: "student",
        roll_number: formData.rollNumber,
        password: formData.password,
        photo: formData.photo, // send captured photo
      });
      alert("Registration successful!");
    } catch (err) {
      alert("Registration failed.");
    }
  };

  return (
    <Layout>
      <main className="sys-card w-full max-w-md p-6">
        <h2 className="text-xl font-semibold text-sys-blue mb-4 text-center">
          Student Registration
        </h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Inputs */}
          <input name="fullName" placeholder="Full Name" onChange={(e) => setFormData({ ...formData, fullName: e.target.value })} required />
          <input name="rollNumber" placeholder="University Roll Number" onChange={(e) => setFormData({ ...formData, rollNumber: e.target.value })} required />
          <input name="email" type="email" placeholder="Email" onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
          <input name="password" type="password" placeholder="Password" onChange={(e) => setFormData({ ...formData, password: e.target.value })} required />

          {/* Camera Capture */}
          <CameraCapture onCapture={handlePhotoCapture} />

          <button type="submit" className="btn-primary">Register</button>
        </form>
      </main>
    </Layout>
  );
}
