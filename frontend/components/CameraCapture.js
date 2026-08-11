/**
 * CameraCapture Component
 * -----------------------
 * Provides webcam access and photo capture.
 * Returns Base64 image data to parent component.
 */

import { useRef, useState } from "react";

export default function CameraCapture({ onCapture }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [photo, setPhoto] = useState(null);

  // Start camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      setStreaming(true);
    } catch (err) {
      console.error("Camera access denied:", err);
    }
  };

  // Capture photo
  const capturePhoto = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const photoData = canvas.toDataURL("image/png"); // Base64 image
    setPhoto(photoData);
    onCapture(photoData); // send to parent
  };

  return (
    <div className="camera-container flex flex-col items-center gap-2">
      <video ref={videoRef} autoPlay playsInline className="rounded-md w-64 h-48 bg-black" />
      <canvas ref={canvasRef} style={{ display: "none" }} />
      <div className="flex gap-2 mt-2">
        {!streaming && (
          <button onClick={startCamera} className="btn-primary">
            Start Camera
          </button>
        )}
        {streaming && (
          <button onClick={capturePhoto} className="btn-secondary">
            Capture Photo
          </button>
        )}
      </div>
      {photo && (
        <img
          src={photo}
          alt="Captured student"
          className="mt-2 w-24 h-24 rounded-full border-2 border-sys-blue"
        />
      )}
    </div>
  );
}
