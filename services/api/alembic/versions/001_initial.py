"""Initial migration — Phase 1 tables

Revision ID: 001
Revises:
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgcrypto is available for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --- roles ---
    op.create_table(
        "roles",
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("name"),
    )

    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(1024), nullable=True),
        sa.Column("contact_fields", postgresql.JSONB(), nullable=True),
        sa.Column("default_currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("website_domain", sa.String(255), nullable=True),
        sa.Column("legal_disclaimer", sa.Text(), nullable=True),
        sa.Column("default_social_rules", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # --- organization_memberships ---
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("owner", "administrator", "editor", "viewer",
                                   name="membership_role_enum"),
                  nullable=False, server_default="viewer"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_organization_memberships_user_id_users",
            ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_sessions_user_id_users",
            ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"])
    op.create_index(op.f("ix_sessions_token_hash"), "sessions", ["token_hash"], unique=True)

    # --- audit_events ---
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_audit_events_organization_id_organizations",
            ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_events_user_id_users",
            ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_org_action", "audit_events", ["organization_id", "action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # --- Seed roles ---
    op.execute("INSERT INTO roles (name, description) VALUES ('owner', 'Full control: users, credentials, organization settings')")
    op.execute("INSERT INTO roles (name, description) VALUES ('administrator', 'Listings, accounts, publishing, templates; cannot manage billing/owner-only settings')")
    op.execute("INSERT INTO roles (name, description) VALUES ('editor', 'Create/edit listings, prepare social content; cannot manage secrets/users/destructive settings')")
    op.execute("INSERT INTO roles (name, description) VALUES ('viewer', 'Read-only access')")


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_org_action", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_sessions_token_hash"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("organization_memberships")
    op.execute("DROP TYPE IF EXISTS membership_role_enum")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")
    op.drop_table("roles")
