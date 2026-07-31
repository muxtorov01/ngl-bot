"""add admin role and user language

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres enums require ALTER TYPE ... ADD VALUE, and it cannot run inside
    # the transaction alembic normally wraps migrations in.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'")

    op.add_column(
        "users",
        sa.Column("language", sa.String(2), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
    # Postgres cannot drop a single enum value; downgrading the enum itself
    # is intentionally left as a no-op (any 'admin' rows must be reassigned
    # to 'user' manually before a full type rebuild if ever required).
