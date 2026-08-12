"""Step-oriented narration abstraction (P0-013.4).

Voice is optional and independent of visual rendering. Production may plug
in a TTS provider; default is text-only mock with no audio blob.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class NarrationProvider(ABC):
    @abstractmethod
    def synthesize_step(self, *, text: str, step_id: str, duration_ms: int = 4000) -> Dict[str, Any]:
        """Return narration payload synchronized with a teaching step."""


class MockNarrationProvider(NarrationProvider):
    def synthesize_step(self, *, text: str, step_id: str, duration_ms: int = 4000) -> Dict[str, Any]:
        clean = (text or "").strip()
        return {
            "provider": "mock",
            "step_id": step_id,
            "text": clean,
            "transcript": clean,
            "audio_url": None,
            "duration_ms": duration_ms or max(2500, min(12000, 40 * max(len(clean), 1))),
            "sync": "with_board_actions",
        }


_narration: Optional[NarrationProvider] = None


def get_narration_provider() -> NarrationProvider:
    global _narration
    if _narration is None:
        _narration = MockNarrationProvider()
    return _narration


def set_narration_provider(provider: Optional[NarrationProvider]) -> None:
    global _narration
    _narration = provider
