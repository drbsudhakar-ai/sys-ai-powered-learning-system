import { useEffect, useState } from "react";

export function narrationChunks(text, limit = 220) {
  const sentences = String(text || "").match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
  const chunks = [];
  sentences.forEach((sentence) => {
    const words = sentence.trim().split(/\s+/).filter(Boolean);
    let current = "";
    words.forEach((word) => {
      const candidate = current ? `${current} ${word}` : word;
      if (current && candidate.length > limit) {
        chunks.push(current);
        current = word;
      } else {
        current = candidate;
      }
    });
    if (current) chunks.push(current);
  });
  return chunks;
}

export default function LectureVoice({ step, playing, rate = 1 }) {
  const [available, setAvailable] = useState(false);
  const [voices, setVoices] = useState([]);
  const [voiceId, setVoiceId] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [status, setStatus] = useState("Voice is off");
  useEffect(() => {
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) return;
    setAvailable(true);
    const update = () => setVoices(window.speechSynthesis.getVoices());
    update(); window.speechSynthesis.addEventListener("voiceschanged", update);
    return () => { window.speechSynthesis.removeEventListener("voiceschanged", update); window.speechSynthesis.cancel(); };
  }, []);
  const text = step?.narration?.transcript || step?.narration?.text || "";
  useEffect(() => {
    if (!available) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    if (!enabled || !playing || !text) { setStatus(enabled ? "Paused" : "Voice is off"); return; }
    let active = true;
    const voice = synth.getVoices().find((v) => v.voiceURI === voiceId);
    // Bounded chunks prevent browser speech engines from silently truncating long sentences.
    const chunks = narrationChunks(text);
    let index = 0;
    function speakNext() {
      if (!active || index >= chunks.length) { if (active) setStatus("Narration finished"); return; }
      const utterance = new SpeechSynthesisUtterance(chunks[index++]);
      if (voice) { utterance.voice = voice; utterance.lang = voice.lang; }
      else utterance.lang = "en-IN";
      utterance.rate = rate;
      utterance.onstart = () => { if (active) setStatus("Speaking"); };
      utterance.onend = () => { if (active) speakNext(); };
      utterance.onerror = () => { if (active) setStatus("Voice unavailable — use the transcript or another voice"); };
      synth.speak(utterance);
    }
    speakNext();
    return () => { active = false; synth.cancel(); };
  }, [available, enabled, playing, text, step?.id, voiceId, rate]);
  return <section className="lecture-voice" aria-label="Lesson narration">
    <div className={`lecture-avatar ${status === "Speaking" ? "is-speaking" : ""}`} aria-hidden="true">SYS</div>
    <div><strong>AI Lecturer · narration</strong><p role="status">{available ? status : "Speech is not supported here — the transcript remains available"}</p></div>
    <button type="button" className="btn-secondary" disabled={!available || !text} onClick={() => setEnabled((value) => !value)}>{enabled ? "Turn voice off" : "Enable voice"}</button>
    <label>Device voice<select value={voiceId} onChange={(event) => setVoiceId(event.target.value)} disabled={!available}><option value="">Default English voice</option>{voices.map((voice) => <option key={voice.voiceURI} value={voice.voiceURI}>{voice.name} ({voice.lang})</option>)}</select></label>
    <small>Uses your browser/device speech service, not Groq. Voice availability varies. Resume or a voice/rate change restarts this stage; selecting another voice does not translate the lesson.</small>
  </section>;
}
