"""add account_overrides to publication_campaigns

Revision ID: a1f2e3d4c5b6
Revises: 9887137cd051
Create Date: 2026-07-13 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1f2e3d4c5b6'
down_revision: Union[str, None] = '9887137cd051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('publication_campaigns',
        sa.Column('account_overrides', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('publication_campaigns', 'account_overrides')
