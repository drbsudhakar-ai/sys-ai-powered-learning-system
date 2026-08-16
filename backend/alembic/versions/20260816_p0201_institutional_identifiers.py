"""Enforce normalized institutional identifiers.

Revision ID: 20260816_p0201_ids
Revises: 20260816_p020_auth
Create Date: 2026-08-16
"""

from alembic import op


revision = "20260816_p0201_ids"
down_revision = "20260816_p020_auth"
branch_labels = None
depends_on = None


def upgrade():
    # Fail closed instead of silently renaming, trimming, merging, or choosing
    # between pre-existing institutional identifiers.
    op.execute(
        """
        DO $migration$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM users
                WHERE lower(role) = 'student'
                  AND (roll_number IS NULL OR btrim(roll_number) = '')
            ) THEN
                RAISE EXCEPTION 'student roll_number is required before P0-020.1 migration';
            END IF;
            IF EXISTS (
                SELECT 1 FROM users
                WHERE lower(role) = 'faculty'
                  AND (employee_code IS NULL OR btrim(employee_code) = '')
            ) THEN
                RAISE EXCEPTION 'faculty employee_code is required before P0-020.1 migration';
            END IF;
            IF EXISTS (
                SELECT 1 FROM users
                WHERE roll_number IS NOT NULL
                  AND roll_number <> upper(btrim(roll_number))
            ) THEN
                RAISE EXCEPTION 'roll_number values must already be trimmed and uppercase';
            END IF;
            IF EXISTS (
                SELECT 1 FROM users
                WHERE employee_code IS NOT NULL
                  AND employee_code <> upper(btrim(employee_code))
            ) THEN
                RAISE EXCEPTION 'employee_code values must already be trimmed and uppercase';
            END IF;
            IF EXISTS (
                SELECT upper(btrim(roll_number))
                FROM users
                WHERE roll_number IS NOT NULL
                GROUP BY upper(btrim(roll_number))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'duplicate normalized roll_number values must be resolved';
            END IF;
            IF EXISTS (
                SELECT upper(btrim(employee_code))
                FROM users
                WHERE employee_code IS NOT NULL
                GROUP BY upper(btrim(employee_code))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'duplicate normalized employee_code values must be resolved';
            END IF;
        END
        $migration$;
        """
    )

    op.execute("DROP INDEX IF EXISTS uq_users_roll_number_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_employee_code_normalized")

    op.create_check_constraint(
        "ck_users_student_roll_required",
        "users",
        "lower(role) <> 'student' OR (roll_number IS NOT NULL AND btrim(roll_number) <> '')",
    )
    op.create_check_constraint(
        "ck_users_faculty_employee_required",
        "users",
        "lower(role) <> 'faculty' OR (employee_code IS NOT NULL AND btrim(employee_code) <> '')",
    )
    op.create_check_constraint(
        "ck_users_roll_number_normalized",
        "users",
        "roll_number IS NULL OR roll_number = upper(btrim(roll_number))",
    )
    op.create_check_constraint(
        "ck_users_employee_code_normalized",
        "users",
        "employee_code IS NULL OR employee_code = upper(btrim(employee_code))",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_roll_number_btrim_upper
        ON users (upper(btrim(roll_number)))
        WHERE roll_number IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_employee_code_btrim_upper
        ON users (upper(btrim(employee_code)))
        WHERE employee_code IS NOT NULL
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_users_employee_code_btrim_upper")
    op.execute("DROP INDEX IF EXISTS uq_users_roll_number_btrim_upper")
    op.drop_constraint("ck_users_employee_code_normalized", "users", type_="check")
    op.drop_constraint("ck_users_roll_number_normalized", "users", type_="check")
    op.drop_constraint("ck_users_faculty_employee_required", "users", type_="check")
    op.drop_constraint("ck_users_student_roll_required", "users", type_="check")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_roll_number_normalized
        ON users (upper(roll_number))
        WHERE roll_number IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_employee_code_normalized
        ON users (upper(employee_code))
        WHERE employee_code IS NOT NULL
        """
    )
