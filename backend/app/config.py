"""
Application configuration
-------------------------
Loads settings from environment variables via python-dotenv.
Keeps the existing SYS dotenv-based architecture (no new settings framework).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent

# Load in order: process env wins over later files; explicit backend/.env is primary.
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv()  # cwd .env last as additional overlay for local tooling


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to backend/.env (or repo-root .env) "
            "and configure required values. Never commit real credentials."
        )
    return str(value).strip()


class Settings:
    """Thin settings object backed by environment variables."""

    @property
    def DATABASE_URL(self) -> str:
        return _require("DATABASE_URL")

    @property
    def SECRET_KEY(self) -> str:
        return _require("SECRET_KEY")

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        try:
            return int(raw)
        except ValueError as exc:
            raise RuntimeError(
                "ACCESS_TOKEN_EXPIRE_MINUTES must be an integer"
            ) from exc


settings = Settings()
