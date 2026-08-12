import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/router";
import DigitalTeachingBoard from "../../../components/lecture/DigitalTeachingBoard";
import LectureControls from "../../../components/lecture/LectureControls";
import AskLecturerPanel from "../../../components/lecture/AskLecturerPanel";
import {
  getApiErrorMessage,
  getMe,
  lectureControl,
  lectureInteract,
  lectureStep,
  openLecture,
} from "../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../src/auth";

const Visual3D = dynamic(() => import("../../../components/lecture/Visual3D"), {
  ssr: false,
  loading: () => <p className="lecture-text">Loading 3D visual…</p>,
});

export default function LectureClassroomPage() {
  const router = useRouter();
  const { id } = router.query;
  const [lecture, setLecture] = useState(null);
  const [error, setError] = useState("");
  const [askOpen, setAskOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [replayKey, setReplayKey] = useState(0);
  const [force2d, setForce2d] = useState(false);
  const [checkAnswer, setCheckAnswer] = useState("");

  const paused = lecture?.lecture_status === "PAUSED";
  const playing = lecture?.lecture_status === "PLAYING";

  const load = useCallback(async () => {
    if (!id) return;
    setBusy(true);
    setError("");
    try {
      const res = await openLecture(id);
      setLecture(res.data);
    } catch (err) {
      if (err.response?.status === 401) {
        clearSession();
        redirectToLogin();
        return;
      }
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [id]);

  useEffect(() => {
    if (!router.isReady || !id) return;
    (async () => {
      if (!getToken()) return redirectToLogin();
      try {
        await getMe();
        await load();
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          redirectToLogin();
        } else setError(getApiErrorMessage(err));
      }
    })();
  }, [router.isReady, id, load]);

  useEffect(() => {
    // Device capability fallback for WebGL
    try {
      const canvas = document.createElement("canvas");
      const ok = !!(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
      if (!ok) setForce2d(true);
    } catch {
      setForce2d(true);
    }
  }, []);

  const apply = (res) => setLecture(res.data);

  const run = async (fn) => {
    setBusy(true);
    setError("");
    try {
      apply(await fn());
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const step = lecture?.current_step;
  const progressLabel = useMemo(() => {
    if (!lecture) return "";
    return `Step ${lecture.current_step_index + 1} / ${lecture.step_count}`;
  }, [lecture]);

  const submitCheck = () =>
    run(() =>
      lectureInteract(id, {
        intent: "CHECK_UNDERSTANDING",
        answer: checkAnswer,
        message: checkAnswer,
      })
    );

  return (
    <div className="lecture-page">
      <header className="lecture-topbar">
        <div>
          <Link href="/learning-sessions" className="lecture-back">
            ← Sessions
          </Link>
          <h1 className="lecture-title">{lecture?.title || "AI Lecturer"}</h1>
          <p className="lecture-subtitle">
            Digital classroom · {lecture?.mode || "…"} · {progressLabel}
            {lecture?.lecture_status ? ` · ${lecture.lecture_status}` : ""}
          </p>
        </div>
        <div className="lecture-top-actions">
          <button type="button" className="btn-secondary" onClick={() => setForce2d((v) => !v)}>
            {force2d ? "Try 3D" : "2D fallback"}
          </button>
        </div>
      </header>

      {error ? <p className="lecture-error">{error}</p> : null}

      <DigitalTeachingBoard
        key={`${step?.id}-${replayKey}`}
        step={step}
        playing={playing && !paused}
        playbackRate={lecture?.playback_rate || 1}
        use3dFallback={force2d && step?.visual_type === "3D_MODEL"}
        Visual3D={Visual3D}
      />

      <div className="lecture-narration" aria-live="polite">
        <strong>Lecturer</strong>
        <p>{step?.narration?.transcript || step?.narration?.text || "…"}</p>
        <details>
          <summary>Narration transcript</summary>
          <p>{step?.narration?.transcript || step?.narration?.text}</p>
        </details>
      </div>

      {step?.interaction?.options?.length ? (
        <div className="lecture-check-controls">
          {step.interaction.options.map((opt) => (
            <button
              key={opt}
              type="button"
              className={checkAnswer === opt ? "btn-primary" : "btn-secondary"}
              onClick={() => setCheckAnswer(opt)}
            >
              {opt}
            </button>
          ))}
          <button type="button" className="btn-primary" disabled={!checkAnswer || busy} onClick={submitCheck}>
            Check
          </button>
        </div>
      ) : null}

      <AskLecturerPanel
        open={askOpen}
        busy={busy}
        onSubmit={({ intent, message }) => run(() => lectureInteract(id, { intent, message }))}
      />

      <LectureControls
        disabled={busy || !lecture}
        paused={paused}
        askOpen={askOpen}
        onPrev={() => run(() => lectureStep(id, { action: "PREV" }))}
        onNext={() => run(() => lectureStep(id, { action: "NEXT" }))}
        onPauseResume={() =>
          run(() => lectureControl(id, { action: paused ? "RESUME" : "PAUSE" }))
        }
        onReplay={() => {
          setReplayKey((k) => k + 1);
          run(() => lectureStep(id, { action: "REPLAY" }));
        }}
        onExplain={() => run(() => lectureInteract(id, { intent: "EXPLAIN_AGAIN" }))}
        onAskToggle={() => setAskOpen((v) => !v)}
        onSlow={() => run(() => lectureControl(id, { action: "SLOW_DOWN" }))}
        onFast={() => run(() => lectureControl(id, { action: "SPEED_UP" }))}
        onComplete={() => run(() => lectureControl(id, { action: "COMPLETE" }))}
      />
    </div>
  );
}
