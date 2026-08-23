"""Add academic_program column to users table

Revision ID: d8027c4ad5d1
Revises: 85afb3dcfb56
Create Date: 2026-08-18 22:52:35.323743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8027c4ad5d1'
down_revision: Union[str, Sequence[str], None] = '85afb3dcfb56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add academic_program column to users table"""
    op.add_column('users', sa.Column('academic_program', sa.String(255), nullable=True))

def downgrade() -> None:
    """Remove academic_program column from users table"""
    op.drop_column('users', 'academic_program')
