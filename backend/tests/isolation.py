"""Fail-closed database isolation for every backend test process.

The configured TEST_DATABASE_URL is a required safety declaration. SQLite test
configuration is materialized as a unique disposable file so threads and all
FastAPI/direct SQLAlchemy sessions share one isolated database for the run.
"""

from __future__ import annotations

import atexit
import gc
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy.engine import URL, Engine, make_url


class UnsafeTestDatabaseError(RuntimeError):
    """Raised before SQLAlchemy can connect to an unsafe test target."""


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env")

DEVELOPMENT_DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
CONFIGURED_TEST_DATABASE_URL = (os.getenv("TEST_DATABASE_URL") or "").strip()


def _is_sqlite_memory(url: URL) -> bool:
    return url.get_backend_name() == "sqlite" and (not url.database or url.database == ":memory:")


def _looks_like_test_target(url: URL) -> bool:
    backend = url.get_backend_name()
    if backend == "sqlite":
        if _is_sqlite_memory(url):
            return True
        return "test" in Path(url.database or "").name.lower()
    if backend in {"postgresql", "postgres"}:
        return "test" in (url.database or "").lower()
    return False


def validate_database_targets(development_url: str, test_url: str) -> tuple[URL, URL]:
    if not development_url:
        raise UnsafeTestDatabaseError("DATABASE_URL is required to prove test isolation")
    if not test_url:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL is required; backend tests never fall back to DATABASE_URL"
        )
    try:
        development = make_url(development_url)
        test = make_url(test_url)
    except Exception as exc:
        raise UnsafeTestDatabaseError("Database test configuration is invalid") from exc
    if development == test:
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL must not equal DATABASE_URL")
    if not _looks_like_test_target(test):
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL must identify an explicit test database")
    return development, test


DEVELOPMENT_URL, _CONFIGURED_TEST_URL = validate_database_targets(
    DEVELOPMENT_DATABASE_URL,
    CONFIGURED_TEST_DATABASE_URL,
)

_DISPOSABLE_DATABASE: Path | None = None
if _CONFIGURED_TEST_URL.get_backend_name() == "sqlite":
    _DISPOSABLE_DATABASE = Path(tempfile.gettempdir()) / (
        f"sys_backend_test_{os.getpid()}_{uuid.uuid4().hex}.db"
    )
    TEST_URL = _CONFIGURED_TEST_URL.set(
        database=_DISPOSABLE_DATABASE.as_posix(),
        query={"check_same_thread": "false"},
    )
else:
    TEST_URL = _CONFIGURED_TEST_URL

TEST_DATABASE_URL = TEST_URL.render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SYS_TEST_MODE"] = "1"
os.environ.setdefault("SECRET_KEY", "sys-backend-tests-only-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

_original_create_engine = sqlalchemy.create_engine


def _is_allowed_engine_url(candidate: URL) -> bool:
    return candidate == TEST_URL or _is_sqlite_memory(candidate) or _looks_like_test_target(candidate)


def guarded_create_engine(url: str | URL, *args: Any, **kwargs: Any) -> Engine:
    candidate = make_url(url)
    if not _is_allowed_engine_url(candidate):
        raise UnsafeTestDatabaseError("Backend tests attempted to create a non-test database engine")
    return _original_create_engine(url, *args, **kwargs)


sqlalchemy.create_engine = guarded_create_engine


def assert_isolated_engine(engine: Engine) -> None:
    if make_url(engine.url) != TEST_URL:
        raise UnsafeTestDatabaseError("Application database engine is not bound to TEST_DATABASE_URL")


def isolated_db_dependency():
    from app import database

    assert_isolated_engine(database.engine)
    session = database.SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def configure_test_app(app) -> None:
    """Bind FastAPI dependencies and direct SessionLocal use to the same test engine."""
    from app import database

    assert_isolated_engine(database.engine)
    app.dependency_overrides[database.get_db] = isolated_db_dependency


def _cleanup_disposable_database() -> None:
    try:
        from app import database
        from sqlalchemy.orm import close_all_sessions

        if make_url(database.engine.url) == TEST_URL:
            close_all_sessions()
            database.engine.dispose()
    except (ImportError, UnsafeTestDatabaseError):
        pass
    gc.collect()
    if _DISPOSABLE_DATABASE is not None:
        _DISPOSABLE_DATABASE.unlink(missing_ok=True)


atexit.register(_cleanup_disposable_database)
