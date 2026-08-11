import React from "react";

export default function EntranceCoachingIllustration({
  size = 120,
  className = "",
  title = "Entrance test coaching",
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
      aria-labelledby="entrance-coaching-title"
    >
      <title id="entrance-coaching-title">{title}</title>

      {/* Background */}
      <rect
        x="12"
        y="12"
        width="136"
        height="136"
        rx="32"
        fill="#FFF1F7"
      />

      {/* Stars */}
      <path
        d="M32 46V58M26 52H38"
        stroke="#F9A8D4"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M125 72V82M120 77H130"
        stroke="#F9A8D4"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* Goal */}
      <circle
        cx="115"
        cy="48"
        r="19"
        fill="white"
        stroke="#EC0A75"
        strokeWidth="4"
      />

      <circle
        cx="115"
        cy="48"
        r="10"
        fill="#FCE7F3"
        stroke="#EC0A75"
        strokeWidth="3"
      />

      <circle cx="115" cy="48" r="4" fill="#EC0A75" />

      {/* Path */}
      <path
        d="M38 112C51 102 54 91 64 87C73 83 79 88 85 77C91 67 99 61 110 52"
        stroke="#F9A8D4"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray="7 7"
      />

      {/* Rocket */}
      <path
        d="M68 38C79 29 94 29 106 35C105 48 99 60 88 68L70 56C67 50 67 44 68 38Z"
        fill="#EC0A75"
      />

      {/* Rocket window */}
      <circle
        cx="91"
        cy="43"
        r="6"
        fill="white"
      />

      {/* Rocket wing */}
      <path
        d="M76 57L63 67L65 52L72 47"
        fill="#BE185D"
      />

      {/* Flame */}
      <path
        d="M72 59C63 62 57 70 58 79C66 76 72 71 76 64L72 59Z"
        fill="#F97316"
      />

      {/* Small flame highlight */}
      <path
        d="M67 66C64 68 62 71 62 74C65 72 67 70 69 67"
        fill="#FBBF24"
      />

      {/* Achievement check */}
      <circle cx="47" cy="112" r="18" fill="#EC0A75" />

      <path
        d="M39 112L45 118L56 106"
        stroke="white"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}