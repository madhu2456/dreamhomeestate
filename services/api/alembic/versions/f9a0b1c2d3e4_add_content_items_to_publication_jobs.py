"""Add content_items JSONB to publication_jobs.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-19

Model already declared content_items for multi-item/thread posts; the
original publication migration never created the column.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE publication_jobs
          ADD COLUMN IF NOT EXISTS content_items JSONB
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE publication_jobs
          DROP COLUMN IF EXISTS content_items
        """
    )
