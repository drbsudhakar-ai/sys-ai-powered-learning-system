"""Provider-neutral AI/LLM abstraction for SYS (P0-013.4).

Routes must never call a vendor SDK directly. Swap MockAIProvider for a
real provider behind the same interface when credentials exist.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AIProvider(ABC):
    """Minimal chat/completion interface used by AI Lecturer orchestration."""
    live = False

    @abstractmethod
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return a structured JSON object (never raw frontend code)."""


class MockAIProvider(AIProvider):
    """Deterministic offline provider for tests and local development.

    Does not invent arbitrary UI code. Returns a signal that the lecturer
    service should assemble a validated teaching plan from domain templates.
    """

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = context or {}
        return {
            "provider": "mock",
            "ok": True,
            "intent": ctx.get("intent") or "TEACHING_PLAN",
            "topic_hint": ctx.get("topic_title") or ctx.get("session_title") or "",
            "subject_hint": ctx.get("subject_name") or "",
            "message": user[:500],
            "system_echo": system[:200],
            "prefer_template": True,
        }


class EchoAIProvider(AIProvider):
    """Tiny stub that echoes context — useful for unit isolation."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"provider": "echo", "user": user, "context": context or {}}


class ConfiguredAIProvider(AIProvider):
    """Read the current administrator configuration on every request."""
    live = True

    def complete_json(self, *, system, user, context=None):
        from app.services.ai_gateway import complete_json
        return complete_json(system=system, user=user, context=context)


_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Live configuration by default; offline mocks require explicit opt-in."""
    global _provider
    if _provider is not None:
        return _provider
    name = (os.getenv("SYS_AI_PROVIDER") or "configured").strip().lower()
    if name == "echo":
        return EchoAIProvider()
    if name == "mock":
        return MockAIProvider()
    return ConfiguredAIProvider()


def set_ai_provider(provider: Optional[AIProvider]) -> None:
    """Test hook to inject a provider."""
    global _provider
    _provider = provider
