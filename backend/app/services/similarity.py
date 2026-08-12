"""Deterministic text similarity / fingerprint helpers for question intelligence."""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Iterable, List, Optional, Tuple


_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")


def normalize_text(text: str) -> str:
    t = (text or "").lower().strip()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t)
    return t


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def similarity_ratio(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def classify_similarity(a: str, b: str) -> str:
    """EXACT_PREVIOUS / SIMILAR / CONCEPT_VARIANT / NOVEL relative to pair."""
    r = similarity_ratio(a, b)
    if r >= 0.97:
        return "EXACT_PREVIOUS"
    if r >= 0.82:
        return "SIMILAR"
    if r >= 0.55:
        return "CONCEPT_VARIANT"
    return "NOVEL"


def find_duplicates(
    candidate_text: str,
    existing: Iterable[Tuple[int, str]],
    *,
    exact_threshold: float = 0.97,
    near_threshold: float = 0.82,
) -> List[dict]:
    hits: List[dict] = []
    for qid, text in existing:
        r = similarity_ratio(candidate_text, text)
        if r >= exact_threshold:
            hits.append({"question_id": qid, "ratio": round(r, 4), "class": "EXACT_PREVIOUS"})
        elif r >= near_threshold:
            hits.append({"question_id": qid, "ratio": round(r, 4), "class": "SIMILAR"})
    hits.sort(key=lambda x: x["ratio"], reverse=True)
    return hits


def diversity_ok(selected_texts: List[str], new_text: str, min_distance: float = 0.82) -> bool:
    """Reject if too similar to an already selected question."""
    for t in selected_texts:
        if similarity_ratio(new_text, t) >= min_distance:
            return False
    return True
