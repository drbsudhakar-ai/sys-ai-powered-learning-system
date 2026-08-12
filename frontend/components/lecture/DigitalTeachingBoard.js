/** Progressive digital teaching board (2D elements + actions). */
import { useEffect, useMemo, useState } from "react";

function Formula({ text }) {
  return (
    <div className="lecture-formula" aria-label={`Formula ${text}`}>
      {text}
    </div>
  );
}

function BoardElement({ el, visible }) {
  if (!visible) return null;
  const t = el.type;
  if (t === "heading") {
    return <h2 className="lecture-heading animate-reveal">{el.text}</h2>;
  }
  if (t === "bullet") {
    return <li className="lecture-bullet animate-reveal">{el.text}</li>;
  }
  if (t === "text" || t === "label") {
    return <p className="lecture-text animate-reveal">{el.text}</p>;
  }
  if (t === "formula") {
    return <Formula text={el.text} />;
  }
  if (t === "callout") {
    return <aside className="lecture-callout animate-reveal">{el.text}</aside>;
  }
  if (t === "arrow") {
    return (
      <div className="lecture-arrow animate-reveal" role="img" aria-label={el.label || "arrow"}>
        <span className="lecture-arrow-line" />
        <span>{el.label || "→"}</span>
      </div>
    );
  }
  if (t === "highlight") {
    return <div className="lecture-highlight-marker animate-pulse-soft">Highlight: {el.target}</div>;
  }
  if (t === "diagram") {
    const shape = el.shape || "box";
    return (
      <div
        className={`lecture-diagram shape-${shape} animate-reveal`}
        style={el.scale ? { transform: `scale(${el.scale})` } : undefined}
        role="img"
        aria-label={el.label || "diagram"}
      >
        <span>{el.label || shape}</span>
      </div>
    );
  }
  return <p className="lecture-text animate-reveal">{el.text || el.id}</p>;
}

export default function DigitalTeachingBoard({
  step,
  playing,
  playbackRate = 1,
  use3dFallback = false,
  Visual3D,
}) {
  const elements = step?.board?.elements || [];
  const actions = step?.board?.actions || [];
  const [revealed, setRevealed] = useState(0);
  const is3d = step?.visual_type === "3D_MODEL" && !use3dFallback;
  const fallback = step?.visual?.fallback_2d;

  useEffect(() => {
    setRevealed(0);
    if (!playing || !elements.length) {
      setRevealed(elements.length);
      return undefined;
    }
    const base = Math.max(350, 900 / Math.max(playbackRate, 0.5));
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setRevealed(i);
      if (i >= elements.length) clearInterval(id);
    }, base);
    return () => clearInterval(id);
  }, [step?.id, playing, playbackRate, elements.length]);

  const actionHint = useMemo(() => actions.join(" · "), [actions]);

  return (
    <section
      className="digital-board"
      aria-live="polite"
      aria-label="Digital teaching board"
    >
      <div className="digital-board-surface">
        <div className="digital-board-meta">
          <span className="digital-board-kind">{step?.kind}</span>
          <span className="digital-board-visual">{step?.visual_type}</span>
          {actionHint ? <span className="digital-board-actions">{actionHint}</span> : null}
        </div>

        {is3d && Visual3D ? (
          <div className="digital-board-stage-3d">
            <Visual3D step={step} playing={playing} />
          </div>
        ) : null}

        {use3dFallback && fallback ? (
          <div className="lecture-fallback animate-reveal">
            <p className="lecture-heading">{fallback.title || "2D view"}</p>
            <p className="lecture-text">{fallback.note || "Showing simplified 2D representation."}</p>
          </div>
        ) : null}

        <ul className="digital-board-elements">
          {elements.map((el, idx) => (
            <BoardElement key={el.id || idx} el={el} visible={idx < revealed} />
          ))}
        </ul>

        {step?.interaction?.prompt ? (
          <div className="lecture-check animate-reveal">
            <p className="lecture-heading">Understanding check</p>
            <p>{step.interaction.prompt}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
