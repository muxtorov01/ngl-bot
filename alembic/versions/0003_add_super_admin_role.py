"""add super admin role

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'")

def downgrade() -> None:
    pass
