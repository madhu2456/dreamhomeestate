"""Quick posts, optional listing on campaigns, media library.

Revision ID: e8f9a0b1c2d3
Revises: b2c3d4e5f6a7
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "publication_campaigns",
        "listing_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "publication_campaigns",
        sa.Column(
            "campaign_kind",
            sa.String(length=32),
            nullable=False,
            server_default="listing",
        ),
    )
    op.add_column(
        "publication_campaigns",
        sa.Column("title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "publication_campaigns",
        sa.Column("body", sa.Text(), nullable=True),
    )
    op.add_column(
        "publication_campaigns",
        sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "media_library_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="image"),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("public_url", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("original_file_name", sa.String(length=255), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_library_org_created",
        "media_library_items",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_library_org_created", table_name="media_library_items")
    op.drop_table("media_library_items")
    op.drop_column("publication_campaigns", "media_urls")
    op.drop_column("publication_campaigns", "body")
    op.drop_column("publication_campaigns", "title")
    op.drop_column("publication_campaigns", "campaign_kind")
    op.alter_column(
        "publication_campaigns",
        "listing_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
