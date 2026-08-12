export default function LectureControls({
  onPrev,
  onNext,
  onPauseResume,
  onReplay,
  onExplain,
  onAskToggle,
  onComplete,
  onSlow,
  onFast,
  paused,
  askOpen,
  disabled,
}) {
  return (
    <div className="lecture-controls" role="toolbar" aria-label="Lecture controls">
      <button type="button" className="btn-secondary" onClick={onPrev} disabled={disabled}>
        ◀ Prev
      </button>
      <button type="button" className="btn-primary" onClick={onPauseResume} disabled={disabled}>
        {paused ? "Resume" : "Pause"}
      </button>
      <button type="button" className="btn-secondary" onClick={onNext} disabled={disabled}>
        Next ▶
      </button>
      <button type="button" className="btn-secondary" onClick={onReplay} disabled={disabled}>
        Replay
      </button>
      <button type="button" className="btn-secondary" onClick={onExplain} disabled={disabled}>
        Explain again
      </button>
      <button type="button" className="btn-secondary" onClick={onAskToggle} disabled={disabled}>
        {askOpen ? "Hide ask" : "Ask Lecturer"}
      </button>
      <button type="button" className="btn-secondary" onClick={onSlow} disabled={disabled}>
        Slow
      </button>
      <button type="button" className="btn-secondary" onClick={onFast} disabled={disabled}>
        Faster
      </button>
      <button type="button" className="btn-primary" onClick={onComplete} disabled={disabled}>
        Complete
      </button>
    </div>
  );
}
