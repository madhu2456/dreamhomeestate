"""create audit_log

Revision ID: b2c3d4e5f6a7
Revises: a1f2e3d4c5b6
Create Date: 2026-07-13 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1f2e3d4c5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ['organization_id'], ['organizations.id'],
            name=op.f('fk_audit_log_organization_id_organizations'),
            ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_audit_log_user_id_users'),
            ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log')),
    )
    op.create_index(op.f('ix_audit_log_organization_id'), 'audit_log', ['organization_id'])
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'])
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'])
    op.create_index(op.f('ix_audit_log_created_at'), 'audit_log', ['created_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_log_created_at'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_action'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_user_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_organization_id'), table_name='audit_log')
    op.drop_table('audit_log')
