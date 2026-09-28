"""add valid_from valid_until and embedding to memories

Revision ID: 5a1b8c7d6e5f
Revises: 4f8c2d9e1a7b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5a1b8c7d6e5f"
down_revision: Union[str, Sequence[str], None] = "4f8c2d9e1a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite & Postgres compatibility
    with op.batch_alter_table("memories") as batch_op:
        batch_op.add_column(sa.Column("valid_from", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("valid_until", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("memories") as batch_op:
        batch_op.drop_column("embedding")
        batch_op.drop_column("valid_until")
        batch_op.drop_column("valid_from")
