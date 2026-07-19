"""Quick posts, optional listing on campaigns, media library.

Revision ID: e8f9a0b1c2d3
Revises: b2c3d4e5f6a7
Create Date: 2026-07-19

Idempotent SQL so partial applies / re-runs do not fail.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # listing_id must allow NULL for freeform quick posts
    op.execute(
        """
        ALTER TABLE publication_campaigns
          ALTER COLUMN listing_id DROP NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE publication_campaigns
          ADD COLUMN IF NOT EXISTS campaign_kind VARCHAR(32) NOT NULL DEFAULT 'listing'
        """
    )
    op.execute(
        """
        ALTER TABLE publication_campaigns
          ADD COLUMN IF NOT EXISTS title VARCHAR(255)
        """
    )
    op.execute(
        """
        ALTER TABLE publication_campaigns
          ADD COLUMN IF NOT EXISTS body TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE publication_campaigns
          ADD COLUMN IF NOT EXISTS media_urls JSONB
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS media_library_items (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
          kind VARCHAR(20) NOT NULL DEFAULT 'image',
          object_key VARCHAR(512) NOT NULL,
          public_url VARCHAR(1024) NOT NULL,
          mime_type VARCHAR(100),
          original_file_name VARCHAR(255),
          width INTEGER,
          height INTEGER,
          size_bytes INTEGER,
          duration_seconds INTEGER,
          created_by UUID REFERENCES users(id) ON DELETE SET NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_media_library_org_created
          ON media_library_items (organization_id, created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_media_library_org_created")
    op.execute("DROP TABLE IF EXISTS media_library_items")
    op.execute("ALTER TABLE publication_campaigns DROP COLUMN IF EXISTS media_urls")
    op.execute("ALTER TABLE publication_campaigns DROP COLUMN IF EXISTS body")
    op.execute("ALTER TABLE publication_campaigns DROP COLUMN IF EXISTS title")
    op.execute("ALTER TABLE publication_campaigns DROP COLUMN IF EXISTS campaign_kind")
    # Do not re-add NOT NULL on listing_id if quick posts already exist
