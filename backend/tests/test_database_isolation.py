"""Regression guards for the mandatory backend test database boundary."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tests import isolation
from app import database


class DatabaseIsolationTests(unittest.TestCase):
    def test_application_engine_uses_only_effective_test_database(self):
        isolation.assert_isolated_engine(database.engine)
        self.assertNotEqual(isolation.DEVELOPMENT_URL, isolation.TEST_URL)

    def test_development_database_engine_is_rejected_before_connect(self):
        with self.assertRaises(isolation.UnsafeTestDatabaseError):
            isolation.guarded_create_engine(isolation.DEVELOPMENT_URL)

    def test_missing_equal_and_non_test_configuration_fail_closed(self):
        with self.assertRaises(isolation.UnsafeTestDatabaseError):
            isolation.validate_database_targets("postgresql://host/dev", "")
        with self.assertRaises(isolation.UnsafeTestDatabaseError):
            isolation.validate_database_targets(
                "postgresql://host/dev", "postgresql://host/dev"
            )
        with self.assertRaises(isolation.UnsafeTestDatabaseError):
            isolation.validate_database_targets(
                "postgresql://host/dev", "postgresql://host/another_dev"
            )

    def test_every_test_module_initializes_tests_before_app_imports(self):
        tests_dir = Path(__file__).resolve().parent
        for path in tests_dir.glob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            first_tests_import = None
            first_app_import = None
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    root = (node.module or "").split(".")[0]
                elif isinstance(node, ast.Import):
                    root = node.names[0].name.split(".")[0]
                else:
                    continue
                if root == "tests" and first_tests_import is None:
                    first_tests_import = node.lineno
                if root == "app" and first_app_import is None:
                    first_app_import = node.lineno
            if first_app_import is not None:
                self.assertIsNotNone(first_tests_import, f"{path.name} bypasses test isolation")
                self.assertLess(first_tests_import, first_app_import, path.name)


if __name__ == "__main__":
    unittest.main()
