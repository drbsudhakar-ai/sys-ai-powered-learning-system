import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import DigitalTeachingBoard from "../../../components/lecture/DigitalTeachingBoard";
import LectureControls from "../../../components/lecture/LectureControls";
import AskLecturerPanel from "../../../components/lecture/AskLecturerPanel";
import LectureVoice from "../../../components/lecture/LectureVoice";
import ClassroomRoster from "../../../components/lecture/ClassroomRoster";
import {
  getApiErrorMessage,
  getMe,
  getLectureQuestions,
  getLecture,
  endCommonLearningSession,
  lectureControl,
  lectureInteract,
  lectureStep,
  openLecture,
} from "../../../src/api";
import { clearSession, getToken, redirectToLogin } from "../../../src/auth";
import styles from "../../../components/lecture/AILecturerClassroom.module.css";

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
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState("");
  const [projecting, setProjecting] = useState(false);
  const pageRef = useRef(null);

  const paused = lecture?.lecture_status === "PAUSED";
  const playing = lecture?.lecture_status === "PLAYING";
  const refreshQuestions = useCallback(async () => {
    try { setHistory((await getLectureQuestions(id)).data.items); setHistoryError(""); }
    catch (err) { setHistoryError(getApiErrorMessage(err, "Question history is unavailable.")); }
  }, [id]);
  useEffect(() => { if (lecture?.activity_id) refreshQuestions(); }, [lecture?.activity_id, refreshQuestions]);
  useEffect(() => {
    const changed = () => setProjecting(document.fullscreenElement === pageRef.current);
    document.addEventListener("fullscreenchange", changed);
    return () => document.removeEventListener("fullscreenchange", changed);
  }, []);
  async function toggleProjection() {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else if (pageRef.current?.requestFullscreen) await pageRef.current.requestFullscreen(); else setError("Fullscreen is unavailable in this browser. Use browser fullscreen instead."); }
    catch { setError("Fullscreen was not permitted. The normal classroom remains available."); }
  }

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
      return true;
    } catch (err) {
      setError(getApiErrorMessage(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const step = lecture?.current_step;
  const visited = lecture?.visited_step_indices || [];
  async function ask(payload) { const ok = await run(() => lectureInteract(id, payload)); if (ok) await refreshQuestions(); return ok; }
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
    <div ref={pageRef} className={`${styles.page} lecture-page`}>
      <Head>
        <title>{lecture?.topic_name || lecture?.title || "AI Lecturer Classroom"} | SYS</title>
        <meta name="description" content="SYS AI Lecturer digital classroom" />
      </Head>
      <header className="lecture-topbar">
        <div>
          <Link href={router.query.course_id ? `/courses/${router.query.course_id}/workspace` : "/learning-sessions"} className="lecture-back">
            ← {router.query.course_id ? "Course workspace" : "Learning sessions"}
          </Link>
          <p className={styles.brand}>SYS — STRENGTHEN YOUR SKILLS · AI LECTURER CLASSROOM</p>
          <h1 className="lecture-title">{lecture?.title || "AI Lecturer"}</h1>
          <p className="lecture-subtitle">
            {[lecture?.course_title, lecture?.subject_name, lecture?.topic_name, lecture?.subtopic_name].filter(Boolean).join(" · ")}
          </p>
          <p className="lecture-subtitle">
            {lecture?.mode || "…"} learning · {progressLabel}
            {lecture?.lecture_status ? ` · ${lecture.lecture_status}` : ""}
          </p>
        </div>
        <div className="lecture-top-actions">
          {lecture?.can_manage_classroom && lecture.mode !== "INDIVIDUAL" && ["IN_PROGRESS", "PAUSED"].includes(lecture.session_status) && <button type="button" className="btn-secondary" disabled={busy} onClick={() => { if (window.confirm("End this common session? This records the class end time; it does not mark students complete.")) run(async () => { await endCommonLearningSession(id); return getLecture(id); }); }}>End common session</button>}
          <button type="button" className="btn-secondary" onClick={toggleProjection}>{projecting ? "Exit projector mode" : "Projector mode"}</button>
          <button type="button" className="btn-secondary" onClick={() => setForce2d((v) => !v)}>
            {force2d ? "Try 3D" : "2D fallback"}
          </button>
        </div>
      </header>

      {lecture?.teaching_plan?.source === "configured_ai" && <p className={styles.sourceNote}>AI-generated lesson · Verify important facts with approved course material. Questions are answered by the configured provider.</p>}
      {lecture && lecture?.teaching_plan?.source !== "configured_ai" && <p className={styles.sourceNote}>Saved template lesson · Not evidence of a live AI-generated lecture. New sessions use your configured provider.</p>}
      {error ? <p className="lecture-error">{error}</p> : null}
      {lecture?.syllabus_review_required && <p role="status" className={styles.sourceNote}>The approved syllabus changed after this saved lesson was prepared. Faculty should verify its coverage. Your lesson history and completion records are preserved.</p>}
      {!lecture && <div className={styles.sourceNote} role="status"><p>{busy ? "Preparing the topic lesson. Generation may take a moment; please do not refresh." : "No lesson loaded. A common classroom must first be prepared by its faculty member."}</p><button type="button" className="btn-primary" disabled={busy} onClick={load}>Retry opening classroom</button></div>}
      {lecture?.can_manage_classroom && lecture.mode !== "INDIVIDUAL" && <ClassroomRoster sessionId={id} />}

      <div className={styles.classroomGrid}>
        <main className={styles.boardColumn}>
          <DigitalTeachingBoard
            key={`${step?.id}-${replayKey}`}
            step={step}
            playing={playing && !paused}
            playbackRate={lecture?.playback_rate || 1}
            use3dFallback={force2d && step?.visual_type === "3D_MODEL"}
            Visual3D={Visual3D}
          />

          <div className="lecture-narration" aria-live="polite">
            <LectureVoice step={step} playing={playing && !paused} rate={lecture?.playback_rate || 1} />
            <strong>SYS AI Lecturer</strong>
            <p>{step?.narration?.transcript || step?.narration?.text || "Preparing your lesson…"}</p>
            <details>
              <summary>Read narration transcript</summary>
              <p>{step?.narration?.transcript || step?.narration?.text}</p>
            </details>
          </div>
        </main>
        <aside className={styles.lessonPanel}>
          <p className={styles.panelEyebrow}>TEACHING JOURNEY</p>
          <h2>Lesson stages</h2>
          <p className={styles.sourceNote}>{visited.length} of {lecture?.step_count || 0} stages visited</p>
          <div className={styles.progressTrack}><span style={{ width: `${lecture ? Math.min(100, visited.length / lecture.step_count * 100) : 0}%` }} /></div>
          <ol className={styles.stageList}>
            {(lecture?.teaching_plan?.steps || []).map((item, index) => (
              <li key={item.id || index} className={index === lecture.current_step_index ? styles.currentStage : visited.includes(index) ? styles.doneStage : ""}>
                <span>{index + 1}</span><button type="button" disabled={busy} onClick={() => run(() => lectureStep(id, { action: "GOTO", step_index: index }))}><strong>{item.title || item.board?.elements?.find((el) => el.type === "heading")?.text || item.kind}</strong><small>{index === lecture.current_step_index ? "Current stage" : visited.includes(index) ? "Visited" : "Not visited"}</small></button>
              </li>
            ))}
          </ol>
          <div className={styles.classroomNote}>Your stage visits, questions and completion are recorded individually. Visiting a stage is not proof of mastery; assessments measure understanding.</div>
        </aside>
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

      <div className={styles.interactionArea}>
        <AskLecturerPanel
          open={askOpen}
          busy={busy}
          onSubmit={ask}
        />
        {lecture && <details className={styles.history}><summary>My questions & explanations ({history.length})</summary>{historyError && <p role="alert">{historyError}</p>}<button type="button" className="btn-secondary" onClick={refreshQuestions}>Refresh history</button>{history.map((entry) => <article key={entry.id}><strong>{entry.question || entry.intent?.replaceAll("_", " ")}</strong><p>{entry.explanation || "No saved explanation for this earlier interaction."}</p><small>{new Date(entry.created_at).toLocaleString()}</small></article>)}{!history.length && <p>No questions recorded yet. Personal questions are not added to the shared class lesson.</p>}</details>}
        {lecture && <section className={styles.recap}><h2>Topic recap</h2><p>{lecture.recap || "Review the final lesson stage."}</p><p>{lecture.lesson_completed ? "Your lesson completion is saved. Continue from your course workspace." : "Review every stage and this recap, then confirm completion. This marks your lesson only, not every student in the class."}</p><Link href={`/courses/${lecture.course_id}/workspace`}>Back to course learning workspace</Link></section>}
      </div>

      <LectureControls
        disabled={busy || !lecture}
        canComplete={lecture?.can_complete}
        completed={lecture?.lesson_completed}
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
        onExplain={() => ask({ intent: "EXPLAIN_AGAIN" })}
        onAskToggle={() => setAskOpen((v) => !v)}
        onSlow={() => run(() => lectureControl(id, { action: "SLOW_DOWN" }))}
        onFast={() => run(() => lectureControl(id, { action: "SPEED_UP" }))}
        onComplete={() => { if (window.confirm("Have you reviewed the lesson and recap? Record your own lesson completion?")) run(() => lectureControl(id, { action: "COMPLETE" })); }}
      />
    </div>
  );
}
