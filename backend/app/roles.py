"""Canonical SYS account roles and permission inheritance."""

from __future__ import annotations


SUPER_ADMIN = "super_admin"
ADMIN = "admin"
FACULTY = "faculty"
STUDENT = "student"

ACCOUNT_ROLES = (SUPER_ADMIN, ADMIN, FACULTY, STUDENT)
ROLE_HIERARCHY = {
    SUPER_ADMIN: 4,
    ADMIN: 3,
    FACULTY: 2,
    STUDENT: 1,
}
ADMIN_PERMISSION_ROLES = (SUPER_ADMIN, ADMIN)
PROVISIONABLE_ROLES = (FACULTY, STUDENT)


def normalize_role(role: str | None) -> str:
    return (role or "").strip().lower()


def is_super_admin_role(role: str | None) -> bool:
    return normalize_role(role) == SUPER_ADMIN


def is_admin_role(role: str | None) -> bool:
    return normalize_role(role) in ADMIN_PERMISSION_ROLES


def grants_any_role(role: str | None, allowed_roles: set[str]) -> bool:
    """Return whether a role has one of the explicitly requested permissions.

    Super Admin inherits Admin permission. Other roles remain exact so an
    ordinary Admin does not silently acquire faculty/student identity scope.
    """

    actual = normalize_role(role)
    allowed = {normalize_role(item) for item in allowed_roles}
    return actual in allowed or (actual == SUPER_ADMIN and ADMIN in allowed)
