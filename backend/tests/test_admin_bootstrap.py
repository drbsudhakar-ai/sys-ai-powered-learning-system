"""Focused tests for the interactive first-administrator bootstrap command."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, utils
from app.cli import BootstrapRefused, create_super_admin


class AdminBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.User.__table__.create(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_successful_bootstrap(self):
        with self.session_factory() as db:
            admin = create_super_admin(
                db,
                email="FIRST.ADMIN@EXAMPLE.COM",
                mobile="+919876543210",
                password="StrongAdminPass123!",
            )
            self.assertEqual(admin.role, "admin")
            self.assertEqual(admin.email, "first.admin@example.com")
            self.assertEqual(admin.mobile_number, "+919876543210")
            self.assertEqual(admin.account_status, "ACTIVE")
            self.assertTrue(admin.email_verified)
            self.assertTrue(admin.mobile_verified)

    def test_duplicate_administrator_is_refused(self):
        with self.session_factory() as db:
            create_super_admin(
                db,
                email="first@example.com",
                mobile="+919876543211",
                password="StrongAdminPass123!",
            )
            with self.assertRaises(BootstrapRefused):
                create_super_admin(
                    db,
                    email="second@example.com",
                    mobile="+919876543212",
                    password="AnotherAdminPass123!",
                )
            self.assertEqual(db.query(models.User).filter(models.User.role == "admin").count(), 1)

    def test_password_is_hashed_immediately(self):
        password = "StrongAdminPass123!"
        with self.session_factory() as db:
            admin = create_super_admin(
                db,
                email="hash@example.com",
                mobile="+919876543213",
                password=password,
            )
            self.assertNotEqual(admin.hashed_password, password)
            self.assertNotIn(password, admin.hashed_password)
            self.assertTrue(utils.verify_password(password, admin.hashed_password))


if __name__ == "__main__":
    unittest.main()
