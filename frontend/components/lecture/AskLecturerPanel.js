import { useState } from "react";

export default function AskLecturerPanel({ open, onSubmit, busy }) {
  const [message, setMessage] = useState("");
  const [intent, setIntent] = useState("ASK");
  if (!open) return null;
  return (
    <aside className="ask-lecturer-panel" aria-label="Ask the lecturer">
      <p className="ask-lecturer-title">Ask without leaving the board</p>
      <div className="ask-lecturer-intents">
        {[
          ["ASK", "Ask"],
          ["DONT_UNDERSTAND", "I don't understand"],
          ["SHOW_EXAMPLE", "Show example"],
          ["SHOW_VISUALLY", "Show visually"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={intent === value ? "btn-primary" : "btn-secondary"}
            onClick={() => setIntent(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={3}
        placeholder="Optional details…"
        className="ask-lecturer-input"
      />
      <button
        type="button"
        className="btn-primary"
        disabled={busy}
        onClick={() => {
          onSubmit({ intent, message });
          setMessage("");
        }}
      >
        {busy ? "Teaching…" : "Send to board"}
      </button>
    </aside>
  );
}
