"""Add role_check constraint to users

Revision ID: 85afb3dcfb56
Revises: 20260816_p021_admin
Create Date: 2026-08-18 13:14:29.888246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85afb3dcfb56'
down_revision: Union[str, Sequence[str], None] = '20260816_p021_admin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role_check constraint to users."""
    op.execute("ALTER TABLE users ADD CONSTRAINT role_check CHECK (role IN ('student', 'faculty', 'admin', 'super_admin'))")
   

def downgrade() -> None:
    """Remove role_check constraint from users."""
    op.execute("ALTER TABLE users DROP CONSTRAINT role_check")
