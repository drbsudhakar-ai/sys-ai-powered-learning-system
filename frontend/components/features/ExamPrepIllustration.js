import React from "react";

export default function ExamPrepIllustration({
  size = 120,
  className = "",
  title = "Competitive exam preparation",
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 160 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-labelledby="exam-prep-title"
    >
      <title id="exam-prep-title">{title}</title>

      {/* Background */}
      <rect
        x="12"
        y="12"
        width="136"
        height="136"
        rx="32"
        fill="#EEF2FF"
      />

      {/* Decorative circles */}
      <circle cx="128" cy="32" r="7" fill="#C7D2FE" />
      <circle cx="31" cy="125" r="5" fill="#C7D2FE" />

      {/* Book */}
      <path
        d="M37 58.5C37 54.91 39.91 52 43.5 52H72C77.52 52 82 56.48 82 62V111C78.69 107.91 74.23 106 69.5 106H43.5C39.91 106 37 103.09 37 99.5V58.5Z"
        fill="white"
        stroke="#4F46E5"
        strokeWidth="4"
      />

      <path
        d="M123 58.5C123 54.91 120.09 52 116.5 52H88C82.48 52 78 56.48 78 62V111C81.31 107.91 85.77 106 90.5 106H116.5C120.09 106 123 103.09 123 99.5V58.5Z"
        fill="white"
        stroke="#4F46E5"
        strokeWidth="4"
      />

      {/* Book center */}
      <path
        d="M80 61V109"
        stroke="#4F46E5"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* Text lines */}
      <path
        d="M48 68H68"
        stroke="#A5B4FC"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M48 78H66"
        stroke="#A5B4FC"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M92 68H112"
        stroke="#A5B4FC"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M92 78H110"
        stroke="#A5B4FC"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* Check badge */}
      <circle cx="117" cy="112" r="20" fill="#4F46E5" />

      <path
        d="M108 112L114 118L126 105"
        stroke="white"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Graduation cap */}
      <path
        d="M80 28L42 45L80 62L118 45L80 28Z"
        fill="#4F46E5"
      />

      <path
        d="M55 51V65C55 70.52 66.19 75 80 75C93.81 75 105 70.52 105 65V51"
        stroke="#3730A3"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M118 45V64"
        stroke="#4F46E5"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <circle cx="118" cy="67" r="4" fill="#F59E0B" />
    </svg>
  );
}