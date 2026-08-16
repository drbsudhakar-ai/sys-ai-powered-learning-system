import { useRef } from "react";
import styles from "./Auth.module.css";

const OTP_LENGTH = 6;

export default function OtpInput({ value, onChange, disabled = false, label = "Verification code" }) {
  const refs = useRef([]);
  const digits = Array.from({ length: OTP_LENGTH }, (_, index) => value[index] || "");

  function setFrom(index, raw) {
    const incoming = raw.replace(/\D/g, "").slice(0, OTP_LENGTH - index);
    const next = [...digits];
    incoming.split("").forEach((digit, offset) => {
      next[index + offset] = digit;
    });
    if (!incoming) next[index] = "";
    onChange(next.join(""));
    const focusIndex = Math.min(index + Math.max(incoming.length, 1), OTP_LENGTH - 1);
    refs.current[focusIndex]?.focus();
  }

  function handleKeyDown(event, index) {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      const next = [...digits];
      next[index - 1] = "";
      onChange(next.join(""));
      refs.current[index - 1]?.focus();
    }
    if (event.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
    if (event.key === "ArrowRight" && index < OTP_LENGTH - 1) refs.current[index + 1]?.focus();
  }

  function handlePaste(event) {
    event.preventDefault();
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
    onChange(pasted);
    refs.current[Math.min(pasted.length, OTP_LENGTH - 1)]?.focus();
  }

  return (
    <fieldset className={styles.otpFieldset}>
      <legend>{label}</legend>
      <div className={styles.otpGrid} onPaste={handlePaste}>
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(element) => { refs.current[index] = element; }}
            type="text"
            inputMode="numeric"
            autoComplete={index === 0 ? "one-time-code" : "off"}
            aria-label={`${label} digit ${index + 1}`}
            value={digit}
            onChange={(event) => setFrom(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            maxLength={1}
            disabled={disabled}
          />
        ))}
      </div>
    </fieldset>
  );
}
