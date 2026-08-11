import React from "react";

export default function AICounsellorIllustration({
  size = 120,
  className = "",
  title = "Personalized AI counsellor",
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
      aria-labelledby="ai-counsellor-title"
    >
      <title id="ai-counsellor-title">{title}</title>

      {/* Background */}
      <rect
        x="12"
        y="12"
        width="136"
        height="136"
        rx="32"
        fill="#FFF7D6"
      />

      {/* AI halo */}
      <circle
        cx="80"
        cy="72"
        r="38"
        fill="#FEF3C7"
      />

      {/* AI head */}
      <rect
        x="50"
        y="43"
        width="60"
        height="52"
        rx="25"
        fill="#FBBF24"
      />

      {/* Antenna */}
      <path
        d="M80 43V34"
        stroke="#D97706"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <circle
        cx="80"
        cy="29"
        r="5"
        fill="#F59E0B"
      />

      {/* AI face */}
      <circle cx="68" cy="65" r="4" fill="white" />
      <circle cx="92" cy="65" r="4" fill="white" />

      <path
        d="M68 78C74 83 86 83 92 78"
        stroke="white"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* AI side nodes */}
      <circle cx="43" cy="66" r="6" fill="#F59E0B" />
      <circle cx="117" cy="66" r="6" fill="#F59E0B" />

      <path
        d="M49 66H43"
        stroke="#D97706"
        strokeWidth="3"
      />

      <path
        d="M111 66H117"
        stroke="#D97706"
        strokeWidth="3"
      />

      {/* Person / support body */}
      <path
        d="M43 127C45 108 55 99 67 99H93C105 99 115 108 117 127"
        fill="#FBBF24"
      />

      {/* Heart */}
      <path
        d="M80 103C75 97 65 100 65 108C65 115 73 120 80 124C87 120 95 115 95 108C95 100 85 97 80 103Z"
        fill="#F97316"
      />

      {/* Sparkles */}
      <path
        d="M31 83L34 90L41 93L34 96L31 103L28 96L21 93L28 90L31 83Z"
        fill="#F59E0B"
      />

      <path
        d="M128 38L131 44L137 47L131 50L128 56L125 50L119 47L125 44L128 38Z"
        fill="#F59E0B"
      />
    </svg>
  );
}