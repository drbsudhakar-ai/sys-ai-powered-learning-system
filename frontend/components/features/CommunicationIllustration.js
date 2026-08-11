import React from "react";

export default function CommunicationIllustration({
  size = 120,
  className = "",
  title = "Communication skills",
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
      aria-labelledby="communication-title"
    >
      <title id="communication-title">{title}</title>

      {/* Background */}
      <rect
        x="12"
        y="12"
        width="136"
        height="136"
        rx="32"
        fill="#ECFDF3"
      />

      {/* Decorative dots */}
      <circle cx="29" cy="38" r="5" fill="#BBF7D0" />
      <circle cx="128" cy="118" r="7" fill="#BBF7D0" />

      {/* Back speech bubble */}
      <path
        d="M43 38H105C111.63 38 117 43.37 117 50V77C117 83.63 111.63 89 105 89H81L68 101V89H43C36.37 89 31 83.63 31 77V50C31 43.37 36.37 38 43 38Z"
        fill="white"
        stroke="#16A34A"
        strokeWidth="4"
      />

      {/* Text */}
      <path
        d="M47 54H101"
        stroke="#86EFAC"
        strokeWidth="5"
        strokeLinecap="round"
      />

      <path
        d="M47 68H88"
        stroke="#86EFAC"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Microphone */}
      <rect
        x="72"
        y="72"
        width="22"
        height="38"
        rx="11"
        fill="#16A34A"
      />

      <path
        d="M64 92C64 103.05 72.95 112 84 112C95.05 112 104 103.05 104 92"
        stroke="#15803D"
        strokeWidth="5"
        strokeLinecap="round"
      />

      <path
        d="M84 112V123"
        stroke="#15803D"
        strokeWidth="5"
        strokeLinecap="round"
      />

      <path
        d="M74 123H94"
        stroke="#15803D"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Sound waves */}
      <path
        d="M112 94C116 90 118 85 118 80"
        stroke="#22C55E"
        strokeWidth="4"
        strokeLinecap="round"
      />

      <path
        d="M121 98C127 92 130 84 130 76"
        stroke="#86EFAC"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}