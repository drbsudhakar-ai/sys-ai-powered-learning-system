"""Structured teaching-plan contract, validation, and visual intelligence (P0-013.4).

LLM output must be shaped into this provider-neutral schema — never arbitrary
executable frontend code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.constants import (
    TEACHING_BOARD_ACTIONS,
    TEACHING_STEP_KINDS,
    TEACHING_VISUAL_TYPES,
)


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def select_visual_type(
    *,
    concept: str,
    domain_hint: str = "",
    prefers_spatial: bool = False,
) -> str:
    """Choose the simplest clear representation (2D unless 3D adds educational value)."""
    text = f"{concept} {domain_hint}".lower()
    spatial_keywords = (
        "3d",
        "vector",
        "molecule",
        "orbital",
        "heart",
        "anatomy",
        "organ",
        "cell structure",
        "geometry solid",
        "projectile",
        "rotation",
        "torque",
        "assembly",
        "terrain",
        "wave propagation",
        "coordinate system",
        "molecular",
        "dna",
        "force system",
    )
    formula_keywords = ("equation", "formula", "f = ma", "law of", "derive", "algebra")
    anim_keywords = ("process", "flow", "circulation", "mechanism", "before/after", "motion")
    chart_keywords = ("trend", "graph", "chart", "distribution", "compare rates")

    if prefers_spatial or any(k in text for k in spatial_keywords):
        return "3D_MODEL"
    if any(k in text for k in formula_keywords):
        return "FORMULA"
    if any(k in text for k in chart_keywords):
        return "CHART"
    if any(k in text for k in anim_keywords):
        return "ANIMATION_2D"
    if "diagram" in text or "flowchart" in text or "map" in text:
        return "DIAGRAM_2D"
    return "BOARD_MIXED"


def validate_teaching_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        raise _http(422, "Teaching plan must be an object")
    if plan.get("version") != 1:
        raise _http(422, "Unsupported teaching plan version")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise _http(422, "Teaching plan requires at least one step")
    seen = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise _http(422, f"Step {i} must be an object")
        sid = step.get("id")
        if not sid or not isinstance(sid, str):
            raise _http(422, f"Step {i} requires string id")
        if sid in seen:
            raise _http(422, f"Duplicate step id: {sid}")
        seen.add(sid)
        kind = (step.get("kind") or "").upper()
        if kind not in TEACHING_STEP_KINDS:
            raise _http(422, f"Invalid step kind: {kind}")
        step["kind"] = kind
        vtype = (step.get("visual_type") or "").upper()
        if vtype not in TEACHING_VISUAL_TYPES:
            raise _http(422, f"Invalid visual_type: {vtype}")
        step["visual_type"] = vtype
        if "narration" not in step or not isinstance(step["narration"], dict):
            raise _http(422, f"Step {sid} requires narration object")
        if not (step["narration"].get("text") or "").strip():
            raise _http(422, f"Step {sid} narration.text is required")
        board = step.get("board") or {}
        if not isinstance(board, dict):
            raise _http(422, f"Step {sid} board must be an object")
        actions = board.get("actions") or []
        if not isinstance(actions, list):
            raise _http(422, f"Step {sid} board.actions must be a list")
        for a in actions:
            if a not in TEACHING_BOARD_ACTIONS:
                raise _http(422, f"Invalid board action '{a}' in step {sid}")
        if "elements" not in board or not isinstance(board["elements"], list):
            board["elements"] = board.get("elements") or []
        step["board"] = board
        if step.get("visual") is not None and not isinstance(step["visual"], dict):
            raise _http(422, f"Step {sid} visual must be an object")
        if vtype == "3D_MODEL":
            visual = step.get("visual") or {}
            if not visual.get("model_type"):
                raise _http(422, f"3D_MODEL step {sid} requires visual.model_type")
            if "fallback_2d" not in visual:
                visual["fallback_2d"] = {
                    "type": "DIAGRAM_2D",
                    "title": visual.get("model_type"),
                    "note": "2D fallback when 3D cannot render",
                }
            step["visual"] = visual
    plan["steps"] = steps
    return plan


def _step(
    *,
    sid: str,
    kind: str,
    purpose: str,
    visual_type: str,
    narration: str,
    elements: List[Dict[str, Any]],
    actions: List[str],
    visual: Optional[Dict[str, Any]] = None,
    interaction: Optional[Dict[str, Any]] = None,
    duration_ms: int = 5000,
) -> Dict[str, Any]:
    return {
        "id": sid,
        "kind": kind,
        "purpose": purpose,
        "visual_type": visual_type,
        "board": {"elements": elements, "actions": actions},
        "visual": visual,
        "narration": {"text": narration, "duration_ms": duration_ms},
        "interaction": interaction,
        "duration_ms": duration_ms,
    }


def plan_newtons_second_law(title: str) -> Dict[str, Any]:
    return {
        "version": 1,
        "title": title or "Newton's Second Law",
        "topic": "Newton's Second Law",
        "representation_policy": "prefer_simplest_clear_visual; use_3d_only_for_spatial_value",
        "domain": "physics",
        "steps": [
            _step(
                sid="n2-1",
                kind="INTRODUCTION",
                purpose="introduce_force_mass_acceleration",
                visual_type="BOARD_MIXED",
                narration="We will learn how force, mass, and acceleration relate.",
                elements=[
                    {"type": "heading", "text": "Newton's Second Law", "id": "h1"},
                    {"type": "bullet", "text": "Force", "id": "b1"},
                    {"type": "bullet", "text": "Mass", "id": "b2"},
                    {"type": "bullet", "text": "Acceleration", "id": "b3"},
                ],
                actions=["reveal", "write"],
                duration_ms=4500,
            ),
            _step(
                sid="n2-2",
                kind="CONCEPT",
                purpose="display_formula",
                visual_type="FORMULA",
                narration="The relationship is written as F equals m a.",
                elements=[{"type": "formula", "text": "F = ma", "id": "f1"}],
                actions=["write", "emphasize"],
                duration_ms=4000,
            ),
            _step(
                sid="n2-3",
                kind="EXPLANATION",
                purpose="animate_block",
                visual_type="ANIMATION_2D",
                narration="Watch a block resting on a surface.",
                elements=[
                    {"type": "diagram", "id": "block", "shape": "rect", "label": "mass m"},
                    {"type": "label", "text": "Block at rest", "id": "l1"},
                ],
                actions=["draw", "reveal"],
                visual={"model_type": "block_force", "animation": ["reveal"]},
                duration_ms=4500,
            ),
            _step(
                sid="n2-4",
                kind="EXPLANATION",
                purpose="apply_force",
                visual_type="ANIMATION_2D",
                narration="Now apply a force to the block.",
                elements=[
                    {"type": "diagram", "id": "block", "shape": "rect", "label": "mass m"},
                    {"type": "arrow", "id": "force", "label": "F", "from": "left", "to": "block"},
                ],
                actions=["draw", "emphasize", "move"],
                visual={"model_type": "block_force", "animation": ["move", "emphasize"]},
                duration_ms=5000,
            ),
            _step(
                sid="n2-5",
                kind="EXPLANATION",
                purpose="show_acceleration",
                visual_type="ANIMATION_2D",
                narration="Acceleration increases as the net force increases.",
                elements=[
                    {"type": "arrow", "id": "force", "label": "F ↑", "emphasize": True},
                    {"type": "label", "text": "a ↑", "id": "acc"},
                    {"type": "highlight", "target": "acc"},
                ],
                actions=["highlight", "transform"],
                duration_ms=5000,
            ),
            _step(
                sid="n2-6",
                kind="EXPLANATION",
                purpose="change_mass_same_force",
                visual_type="ANIMATION_2D",
                narration="Keep force the same and increase mass. Acceleration drops.",
                elements=[
                    {"type": "diagram", "id": "block", "shape": "rect", "label": "m ↑", "scale": 1.4},
                    {"type": "arrow", "id": "force", "label": "F (same)"},
                    {"type": "label", "text": "a ↓", "id": "acc2"},
                ],
                actions=["compare", "transform"],
                duration_ms=5500,
            ),
            _step(
                sid="n2-7",
                kind="EXPLANATION",
                purpose="spatial_force_vectors",
                visual_type="3D_MODEL",
                narration="In space, forces are vectors. Observe direction and magnitude.",
                elements=[{"type": "callout", "text": "3D force vectors", "id": "c1"}],
                actions=["rotate", "highlight", "zoom"],
                visual={
                    "model_type": "force_vectors",
                    "objects": ["origin", "force_vector", "acceleration_vector"],
                    "animation": ["rotate", "highlight", "zoom"],
                    "fallback_2d": {
                        "type": "DIAGRAM_2D",
                        "title": "Force vectors (2D)",
                        "elements": [
                            {"type": "arrow", "label": "F"},
                            {"type": "arrow", "label": "a"},
                        ],
                    },
                },
                duration_ms=6000,
            ),
            _step(
                sid="n2-8",
                kind="EXAMPLE",
                purpose="numerical_example",
                visual_type="BOARD_MIXED",
                narration="Example: mass 2 kilograms, force 10 newtons. Acceleration is 5 meters per second squared.",
                elements=[
                    {"type": "heading", "text": "Worked example", "id": "ex"},
                    {"type": "text", "text": "m = 2 kg, F = 10 N", "id": "givens"},
                    {"type": "formula", "text": "a = F / m = 10 / 2 = 5 m/s²", "id": "sol"},
                ],
                actions=["write", "reveal"],
                duration_ms=7000,
            ),
            _step(
                sid="n2-9",
                kind="CHECK",
                purpose="check_understanding",
                visual_type="TEXT",
                narration="Quick check: if force doubles and mass stays the same, what happens to acceleration?",
                elements=[{"type": "heading", "text": "Check understanding", "id": "chk"}],
                actions=["reveal"],
                interaction={
                    "type": "CHECK_UNDERSTANDING",
                    "prompt": "If F doubles and m is unchanged, acceleration…",
                    "options": ["doubles", "halves", "stays the same"],
                    "correct": "doubles",
                },
                duration_ms=8000,
            ),
            _step(
                sid="n2-10",
                kind="SUMMARY",
                purpose="summarize",
                visual_type="FORMULA",
                narration="Remember: net force equals mass times acceleration.",
                elements=[
                    {"type": "formula", "text": "F_net = m a", "id": "sum"},
                    {"type": "bullet", "text": "Larger F → larger a", "id": "s1"},
                    {"type": "bullet", "text": "Larger m → smaller a", "id": "s2"},
                ],
                actions=["reveal", "emphasize"],
                duration_ms=5000,
            ),
        ],
    }


def plan_heart_circulation(title: str) -> Dict[str, Any]:
    return {
        "version": 1,
        "title": title or "Human Heart — Blood Circulation",
        "topic": "Human Heart — Blood Circulation",
        "representation_policy": "3d_for_spatial_anatomy; animate_flow_stepwise",
        "domain": "biology",
        "steps": [
            _step(
                sid="ht-1",
                kind="INTRODUCTION",
                purpose="introduce_heart",
                visual_type="DIAGRAM_2D",
                narration="The heart is a muscular pump that moves blood through the body.",
                elements=[
                    {"type": "heading", "text": "The Human Heart", "id": "h1"},
                    {"type": "diagram", "id": "heart_simple", "shape": "heart", "label": "Heart"},
                ],
                actions=["reveal", "draw"],
                duration_ms=4500,
            ),
            _step(
                sid="ht-2",
                kind="CONCEPT",
                purpose="chambers_appear",
                visual_type="DIAGRAM_2D",
                narration="Four chambers appear: two atria and two ventricles.",
                elements=[
                    {"type": "label", "text": "Right atrium", "id": "ra"},
                    {"type": "label", "text": "Right ventricle", "id": "rv"},
                    {"type": "label", "text": "Left atrium", "id": "la"},
                    {"type": "label", "text": "Left ventricle", "id": "lv"},
                ],
                actions=["reveal", "annotate"],
                duration_ms=5500,
            ),
            _step(
                sid="ht-3",
                kind="EXPLANATION",
                purpose="introduce_3d_heart",
                visual_type="3D_MODEL",
                narration="A spatial model helps you see chamber positions.",
                elements=[{"type": "callout", "text": "3D heart model", "id": "c3d"}],
                actions=["reveal", "zoom"],
                visual={
                    "model_type": "heart",
                    "objects": ["heart", "chambers"],
                    "animation": ["reveal"],
                    "fallback_2d": {"type": "DIAGRAM_2D", "title": "Heart chambers (2D)"},
                },
                duration_ms=5000,
            ),
            _step(
                sid="ht-4",
                kind="EXPLANATION",
                purpose="rotate_model",
                visual_type="3D_MODEL",
                narration="Rotate slowly to locate front and back.",
                elements=[],
                actions=["rotate"],
                visual={
                    "model_type": "heart",
                    "animation": ["rotate"],
                    "fallback_2d": {"type": "DIAGRAM_2D", "title": "Heart outline"},
                },
                duration_ms=5000,
            ),
            _step(
                sid="ht-5",
                kind="EXPLANATION",
                purpose="highlight_right_atrium",
                visual_type="3D_MODEL",
                narration="Highlight the right atrium — blood enters here from the body.",
                elements=[{"type": "highlight", "target": "right_atrium"}],
                actions=["highlight", "annotate"],
                visual={
                    "model_type": "heart",
                    "objects": ["right_atrium"],
                    "animation": ["highlight"],
                    "fallback_2d": {"type": "DIAGRAM_2D", "title": "Right atrium"},
                },
                duration_ms=5000,
            ),
            _step(
                sid="ht-6",
                kind="EXPLANATION",
                purpose="animate_blood_flow",
                visual_type="ANIMATION_2D",
                narration="Blood flows from the right atrium into the right ventricle.",
                elements=[
                    {"type": "arrow", "id": "flow1", "label": "flow", "from": "ra", "to": "rv"},
                ],
                actions=["move", "emphasize"],
                visual={"model_type": "circulation", "animation": ["move"]},
                duration_ms=5500,
            ),
            _step(
                sid="ht-7",
                kind="EXPLANATION",
                purpose="next_chamber",
                visual_type="3D_MODEL",
                narration="Next, the right ventricle sends blood toward the lungs.",
                elements=[{"type": "highlight", "target": "right_ventricle"}],
                actions=["highlight"],
                visual={
                    "model_type": "heart",
                    "objects": ["right_ventricle", "pulmonary_path"],
                    "animation": ["highlight", "connect"],
                    "fallback_2d": {"type": "DIAGRAM_2D", "title": "To the lungs"},
                },
                duration_ms=5500,
            ),
            _step(
                sid="ht-8",
                kind="EXPLANATION",
                purpose="continue_flow",
                visual_type="ANIMATION_2D",
                narration="Oxygen-rich blood returns to the left side of the heart.",
                elements=[
                    {"type": "arrow", "id": "flow2", "label": "O₂ blood", "from": "lungs", "to": "la"},
                ],
                actions=["move", "connect"],
                duration_ms=5500,
            ),
            _step(
                sid="ht-9",
                kind="CONCEPT",
                purpose="introduce_lungs",
                visual_type="DIAGRAM_2D",
                narration="The lungs oxygenate the blood before it returns to the heart.",
                elements=[
                    {"type": "diagram", "id": "lungs", "shape": "ellipse", "label": "Lungs"},
                    {"type": "label", "text": "Gas exchange", "id": "gx"},
                ],
                actions=["reveal", "annotate"],
                duration_ms=5000,
            ),
            _step(
                sid="ht-10",
                kind="APPLICATION",
                purpose="full_path",
                visual_type="ANIMATION_2D",
                narration="Follow the full circulation path once more.",
                elements=[
                    {"type": "diagram", "id": "loop", "shape": "cycle", "label": "Systemic + pulmonary"},
                ],
                actions=["replay", "emphasize"],
                duration_ms=6000,
            ),
            _step(
                sid="ht-11",
                kind="CHECK",
                purpose="check_understanding",
                visual_type="TEXT",
                narration="Where does blood go after the right ventricle?",
                elements=[{"type": "heading", "text": "Check understanding", "id": "chk"}],
                actions=["reveal"],
                interaction={
                    "type": "CHECK_UNDERSTANDING",
                    "prompt": "After the right ventricle, blood goes to the…",
                    "options": ["lungs", "left atrium", "aorta"],
                    "correct": "lungs",
                },
                duration_ms=8000,
            ),
            _step(
                sid="ht-12",
                kind="SUMMARY",
                purpose="summary",
                visual_type="BOARD_MIXED",
                narration="The heart pumps in a coordinated loop: body, right heart, lungs, left heart, body.",
                elements=[
                    {"type": "bullet", "text": "Right side → lungs", "id": "s1"},
                    {"type": "bullet", "text": "Left side → body", "id": "s2"},
                ],
                actions=["reveal"],
                duration_ms=5000,
            ),
        ],
    }


def plan_generic_topic(title: str, topic: str, subject: str = "") -> Dict[str, Any]:
    """Fallback step-by-step plan when no domain template matches."""
    visual = select_visual_type(concept=topic or title, domain_hint=subject)
    use_3d = visual == "3D_MODEL"
    steps = [
        _step(
            sid="g-1",
            kind="INTRODUCTION",
            purpose="introduce_topic",
            visual_type="BOARD_MIXED",
            narration=f"Today we will learn about {topic or title}.",
            elements=[
                {"type": "heading", "text": topic or title, "id": "h1"},
                {"type": "bullet", "text": "What it is", "id": "b1"},
                {"type": "bullet", "text": "Why it matters", "id": "b2"},
            ],
            actions=["reveal", "write"],
        ),
        _step(
            sid="g-2",
            kind="CONCEPT",
            purpose="core_idea",
            visual_type="DIAGRAM_2D" if not use_3d else "3D_MODEL",
            narration="Here is the core idea, shown visually rather than as a long paragraph.",
            elements=[{"type": "diagram", "id": "core", "shape": "box", "label": topic or "Concept"}],
            actions=["draw", "annotate"],
            visual=(
                {
                    "model_type": "concept_space",
                    "animation": ["rotate", "highlight"],
                    "fallback_2d": {"type": "DIAGRAM_2D", "title": topic or title},
                }
                if use_3d
                else {"model_type": "concept_map", "animation": ["reveal"]}
            ),
        ),
        _step(
            sid="g-3",
            kind="EXPLANATION",
            purpose="stepwise_explain",
            visual_type="ANIMATION_2D",
            narration="We break the idea into smaller parts and reveal each one.",
            elements=[
                {"type": "bullet", "text": "Part A", "id": "p1"},
                {"type": "bullet", "text": "Part B", "id": "p2"},
                {"type": "arrow", "id": "link", "from": "p1", "to": "p2"},
            ],
            actions=["reveal", "connect", "emphasize"],
        ),
        _step(
            sid="g-4",
            kind="EXAMPLE",
            purpose="worked_example",
            visual_type="BOARD_MIXED",
            narration="An example builds on the board one line at a time.",
            elements=[
                {"type": "heading", "text": "Example", "id": "ex"},
                {"type": "text", "text": "Given…", "id": "g"},
                {"type": "text", "text": "Therefore…", "id": "t"},
            ],
            actions=["write", "reveal"],
        ),
        _step(
            sid="g-5",
            kind="CHECK",
            purpose="check_understanding",
            visual_type="TEXT",
            narration="Pause and check your understanding before we continue.",
            elements=[{"type": "heading", "text": "Check understanding", "id": "chk"}],
            actions=["reveal"],
            interaction={
                "type": "CHECK_UNDERSTANDING",
                "prompt": f"Can you state the main idea of {topic or title} in one sentence?",
                "options": None,
                "correct": None,
            },
        ),
        _step(
            sid="g-6",
            kind="SUMMARY",
            purpose="summary",
            visual_type="BOARD_MIXED",
            narration="Summary: review the key points on the board.",
            elements=[
                {"type": "bullet", "text": "Key point 1", "id": "s1"},
                {"type": "bullet", "text": "Key point 2", "id": "s2"},
            ],
            actions=["reveal", "emphasize"],
        ),
    ]
    return {
        "version": 1,
        "title": title or topic,
        "topic": topic or title,
        "representation_policy": "prefer_simplest_clear_visual; use_3d_only_for_spatial_value",
        "domain": subject or "general",
        "steps": steps,
    }


def build_teaching_plan(
    *,
    title: str,
    topic_title: str = "",
    subject_name: str = "",
    objectives: Optional[List[str]] = None,
) -> Dict[str, Any]:
    blob = f"{title} {topic_title} {subject_name} {' '.join(objectives or [])}".lower()
    if "newton" in blob or "second law" in blob or "f = ma" in blob or "f=ma" in blob:
        plan = plan_newtons_second_law(title)
    elif "heart" in blob or "circulation" in blob or "blood flow" in blob:
        plan = plan_heart_circulation(title)
    else:
        plan = plan_generic_topic(title, topic_title or title, subject_name)
    if objectives:
        plan["objectives"] = list(objectives)
    return validate_teaching_plan(plan)


def build_remediation_steps(
    *,
    intent: str,
    message: str,
    current_step: Dict[str, Any],
    topic: str,
) -> List[Dict[str, Any]]:
    """Focused board-first response steps (not a chat transcript dump)."""
    intent = (intent or "").upper()
    base_id = f"rem-{current_step.get('id', 'x')}"
    if intent in ("DONT_UNDERSTAND", "EXPLAIN_AGAIN", "SHOW_VISUALLY"):
        vtype = select_visual_type(concept=message or current_step.get("purpose", ""), domain_hint=topic)
        return [
            _step(
                sid=f"{base_id}-1",
                kind="REMEDIATION",
                purpose="re_explain_visually",
                visual_type=vtype if vtype != "TEXT" else "ANIMATION_2D",
                narration="Let's look at this again on the board, one piece at a time.",
                elements=[
                    {"type": "heading", "text": "Let's revisit", "id": "rh"},
                    {"type": "callout", "text": (message or current_step.get("purpose") or "")[:160], "id": "rc"},
                    {"type": "diagram", "id": "rv", "shape": "box", "label": "Focus"},
                ],
                actions=["erase", "reveal", "highlight", "annotate"],
                visual=(
                    {
                        "model_type": (current_step.get("visual") or {}).get("model_type") or "concept_space",
                        "animation": ["highlight", "zoom"],
                        "fallback_2d": {"type": "DIAGRAM_2D", "title": "Re-explanation"},
                    }
                    if vtype == "3D_MODEL"
                    else None
                ),
                duration_ms=6000,
            )
        ]
    if intent == "SHOW_EXAMPLE":
        return [
            _step(
                sid=f"{base_id}-ex",
                kind="EXAMPLE",
                purpose="another_example",
                visual_type="BOARD_MIXED",
                narration="Here is another example constructed step by step.",
                elements=[
                    {"type": "heading", "text": "Another example", "id": "exh"},
                    {"type": "text", "text": "Step A", "id": "exa"},
                    {"type": "text", "text": "Step B", "id": "exb"},
                    {"type": "formula", "text": "Result", "id": "exr"},
                ],
                actions=["write", "reveal"],
                duration_ms=6500,
            )
        ]
    if intent == "ASK":
        return [
            _step(
                sid=f"{base_id}-ask",
                kind="EXPLANATION",
                purpose="answer_on_board",
                visual_type="BOARD_MIXED",
                narration="Good question. Watch the board as we answer it visually.",
                elements=[
                    {"type": "heading", "text": "Your question", "id": "qh"},
                    {"type": "callout", "text": (message or "")[:200] or "Clarification", "id": "qm"},
                    {"type": "bullet", "text": "Key idea", "id": "qa"},
                    {"type": "diagram", "id": "qd", "shape": "box", "label": "Visual answer"},
                ],
                actions=["write", "draw", "highlight"],
                duration_ms=7000,
            )
        ]
    if intent == "CHECK_UNDERSTANDING":
        return [
            _step(
                sid=f"{base_id}-chk",
                kind="CHECK",
                purpose="extra_check",
                visual_type="TEXT",
                narration="Try this short check, then we continue.",
                elements=[{"type": "heading", "text": "Quick check", "id": "qc"}],
                actions=["reveal"],
                interaction={
                    "type": "CHECK_UNDERSTANDING",
                    "prompt": message or "What is the main idea of this step?",
                    "options": None,
                    "correct": None,
                },
                duration_ms=6000,
            )
        ]
    # CONTINUE / GO_BACK / SLOW_DOWN handled as controls, not new steps
    return []


def enrich_step_narration(step: Dict[str, Any], narration_payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(step)
    n = dict(out.get("narration") or {})
    n.update(
        {
            "text": narration_payload.get("text") or n.get("text"),
            "transcript": narration_payload.get("transcript") or n.get("text"),
            "audio_url": narration_payload.get("audio_url"),
            "duration_ms": narration_payload.get("duration_ms") or n.get("duration_ms"),
            "provider": narration_payload.get("provider"),
        }
    )
    out["narration"] = n
    return out
