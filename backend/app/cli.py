"""Interactive SYS backend administration commands."""

from __future__ import annotations

import argparse
import getpass
import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.orm import Session

from app import database, models, utils
from app.services import authentication as auth_service


class BootstrapRefused(RuntimeError):
    pass


def create_super_admin(
    db: Session,
    *,
    email: str,
    mobile: str,
    password: str,
) -> models.User:
    if db.query(models.User).filter(models.User.role == "admin").first():
        raise BootstrapRefused("An administrator already exists")
    try:
        normalized_email = auth_service.normalize_email(email)
        normalized_mobile = auth_service.normalize_mobile(mobile)
        utils.validate_password(password)
    except ValueError as exc:
        raise BootstrapRefused(str(exc)) from exc

    admin = models.User(
        name="SYS Administrator",
        email=normalized_email,
        institutional_email=normalized_email,
        institutional_mobile=normalized_mobile,
        mobile_number=normalized_mobile,
        email_verified=True,
        mobile_verified=True,
        mobile_is_personal=True,
        hashed_password=utils.hash_password(password),
        role="admin",
        employee_code=f"SYS-ADMIN-{uuid.uuid4().hex[:10].upper()}",
        is_active=True,
        account_status=auth_service.ACCOUNT_ACTIVE,
        session_version=1,
        password_changed_at=auth_service.utcnow(),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    password_prompt: Callable[[str], str] = getpass.getpass,
    session_factory: Callable[[], Session] = database.SessionLocal,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "create-super-admin",
        help="Interactively create the first SYS administrator",
    )
    args = parser.parse_args(argv)

    if args.command != "create-super-admin":
        parser.error("Unsupported command")

    email = input_fn("Institutional email: ").strip()
    mobile = input_fn("Personal mobile (E.164, for example +919876543210): ").strip()
    password = password_prompt("Password: ")
    confirmation = password_prompt("Confirm password: ")
    if password != confirmation:
        print("Administrator was not created: passwords do not match.")
        return 2

    db = session_factory()
    try:
        create_super_admin(db, email=email, mobile=mobile, password=password)
    except BootstrapRefused as exc:
        db.rollback()
        print(f"Administrator was not created: {exc}.")
        return 1
    finally:
        db.close()

    print("SYS administrator created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
