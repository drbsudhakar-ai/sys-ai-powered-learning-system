"""Backend test-package configuration.

Keep the integration suite isolated from every developer or production database.
This module is imported before any ``tests.*`` module loads the application.
"""

from __future__ import annotations

import atexit
import os
import tempfile
import uuid
from pathlib import Path


_TEST_DATABASE = Path(tempfile.gettempdir()) / (
    f"sys_backend_tests_{os.getpid()}_{uuid.uuid4().hex}.db"
)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE.as_posix()}?check_same_thread=false"
os.environ.setdefault("SECRET_KEY", "sys-backend-tests-only-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")


def _dispose_test_engine() -> None:
    try:
        from app.database import engine

        engine.dispose()
    except ImportError:
        pass


atexit.register(_dispose_test_engine)
