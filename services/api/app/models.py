"""SQLAlchemy 2.0 declarative models for RealEstateSocial Phase 1."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------- ENUMS ----------

class MembershipRole(str, enum.Enum):
    owner = "owner"
    administrator = "administrator"
    editor = "editor"
    viewer = "viewer"


class ListingStatus(str, enum.Enum):
    draft = "draft"
    ready_for_review = "ready_for_review"
    approved = "approved"
    published = "published"
    paused = "paused"
    sold = "sold"
    rented = "rented"
    expired = "expired"
    archived = "archived"


class TransactionType(str, enum.Enum):
    sale = "sale"
    rent = "rent"
    lease = "lease"
    other = "other"


class ProviderEnum(str, enum.Enum):
    instagram = "instagram"
    x = "x"
    mock = "mock"


class AccountType(str, enum.Enum):
    personal = "personal"
    business = "business"
    creator = "creator"
    page = "page"


class AccountConnectionStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"
    error = "error"


class PropertyType(str, enum.Enum):
    apartment = "apartment"
    house = "house"
    villa = "villa"
    plot = "plot"
    commercial = "commercial"
    office = "office"
    shop = "shop"
    warehouse = "warehouse"
    other = "other"


class FurnishingStatus(str, enum.Enum):
    unfurnished = "unfurnished"
    semi_furnished = "semi_furnished"
    furnished = "furnished"


class ConstructionStatus(str, enum.Enum):
    ready_to_move = "ready_to_move"
    under_construction = "under_construction"
    new_launch = "new_launch"


class OwnershipType(str, enum.Enum):
    freehold = "freehold"
    leasehold = "leasehold"
    power_of_attorney = "power_of_attorney"
    cooperative = "cooperative"


class MediaKind(str, enum.Enum):
    image = "image"
    video = "video"


class MediaProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


# ---------- HELPER ----------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------- MODELS ----------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # contact fields stored as JSONB
    contact_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    website_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legal_disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_social_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization", lazy="selectin"
    )
    listings: Mapped[list["Listing"]] = relationship(
        back_populates="organization", lazy="selectin"
    )
    social_accounts: Mapped[list["SocialAccount"]] = relationship(
        back_populates="organization", lazy="selectin"
    )
    content_templates: Mapped[list["ContentTemplate"]] = relationship(
        back_populates="organization", lazy="selectin"
    )
    publication_campaigns: Mapped[list["PublicationCampaign"]] = relationship(
        back_populates="organization", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role_enum",
             create_type=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=MembershipRole.viewer,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership {self.user_id} in {self.organization_id} as {self.role}>"


class Role(Base):
    """Reference table documenting available roles and their descriptions."""
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Session(Base):
    """Server-side session record keyed by a hashed session id."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditEvent(Base):
    """Immutable audit log."""
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org_action", "organization_id", "action"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AuditLogEntry(Base):
    """Structured audit log for security/compliance tracking."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )


class Listing(Base):
    """Real estate listing scoped to an organization."""

    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_listings_org_slug"),
        UniqueConstraint(
            "organization_id", "public_reference_number", name="uq_listings_org_ref"
        ),
        Index("ix_listings_org_status", "organization_id", "listing_status"),
        Index("ix_listings_org_created", "organization_id", "created_at"),
        Index("ix_listings_published_at", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    public_reference_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    listing_status: Mapped[ListingStatus] = mapped_column(
        Enum(
            ListingStatus,
            name="listing_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ListingStatus.draft,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(
            PropertyType,
            name="property_type_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    negotiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maintenance_charges: Mapped[int | None] = mapped_column(Integer, nullable=True)

    area: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="sqft")
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balconies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    furnishing_status: Mapped[FurnishingStatus | None] = mapped_column(
        Enum(
            FurnishingStatus,
            name="furnishing_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    construction_status: Mapped[ConstructionStatus | None] = mapped_column(
        Enum(
            ConstructionStatus,
            name="construction_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    ownership_type: Mapped[OwnershipType | None] = mapped_column(
        Enum(
            OwnershipType,
            name="ownership_type_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    address_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    state_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_selling_points: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    nearby_landmarks: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_contact: Mapped[str | None] = mapped_column(String(50), nullable=True)

    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    og_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    auto_distribute: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="listings")
    media: Mapped[list["ListingMedia"]] = relationship(
        back_populates="listing", lazy="selectin", cascade="all, delete-orphan"
    )
    versions: Mapped[list["ListingVersion"]] = relationship(
        back_populates="listing", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Listing {self.slug}>"


class ListingMedia(Base):
    """Images and videos attached to a listing."""

    __tablename__ = "listing_media"
    __table_args__ = (
        Index("ix_listing_media_listing_id", "listing_id"),
        Index("ix_listing_media_org_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[MediaKind] = mapped_column(
        Enum(
            MediaKind,
            name="media_kind_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    original_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(500), nullable=True)

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_status: Mapped[MediaProcessingStatus] = mapped_column(
        Enum(
            MediaProcessingStatus,
            name="media_processing_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=MediaProcessingStatus.pending,
    )
    variants: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    listing: Mapped[Listing] = relationship(back_populates="media")

    def __repr__(self) -> str:
        return f"<ListingMedia {self.original_file_name}>"


class SocialAccount(Base):
    """Connected social platform account scoped to an organization."""

    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider", "provider_account_id",
            name="uq_social_accounts_org_provider_account",
        ),
        Index("ix_social_accounts_org_provider_status", "organization_id", "provider", "connection_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[ProviderEnum] = mapped_column(
        Enum(
            ProviderEnum,
            name="provider_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    account_type: Mapped[AccountType | None] = mapped_column(
        Enum(
            AccountType,
            name="account_type_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    connection_status: Mapped[AccountConnectionStatus] = mapped_column(
        Enum(
            AccountConnectionStatus,
            name="account_connection_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AccountConnectionStatus.active,
    )
    granted_scopes: Mapped[list[str] | None] = mapped_column(ARRAY(String(255)), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_publication_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    capabilities_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_default_destination: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="social_accounts")
    credentials: Mapped["EncryptedOAuthCredentials | None"] = relationship(
        back_populates="social_account",
        lazy="selectin",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SocialAccount {self.provider.value}:{self.username}>"


class EncryptedOAuthCredentials(Base):
    """Encrypted OAuth tokens for a social account."""

    __tablename__ = "encrypted_oauth_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    social_account: Mapped[SocialAccount] = relationship(back_populates="credentials")


class ListingVersion(Base):
    """Immutable snapshot of a listing at a point in time."""

    __tablename__ = "listing_versions"
    __table_args__ = (
        UniqueConstraint("listing_id", "version_number", name="uq_listing_versions_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    listing: Mapped[Listing] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<ListingVersion {self.listing_id}#{self.version_number}>"


class ContentTemplate(Base):
    """Sandboxed Jinja2 template for rendering social content."""

    __tablename__ = "content_templates"
    __table_args__ = (
        Index("ix_content_templates_org_platform", "organization_id", "platform"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform: Mapped[ProviderEnum] = mapped_column(
        Enum(
            ProviderEnum,
            name="provider_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    campaign_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)

    title_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="content_templates")
    template_versions: Mapped[list["TemplateVersion"]] = relationship(
        back_populates="template", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContentTemplate {self.name}@{self.platform.value}>"


# ──── Phase 5: Publication enums ────────────────────────────────────


class JobStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    queued = "queued"
    publishing = "publishing"
    partially_published = "partially_published"
    published = "published"
    partial_success = "partial_success"
    failed = "failed"
    cancelled = "cancelled"


class AttemptStatus(str, enum.Enum):
    success = "success"
    failed = "failed"


# ──── Phase 5: Publication models ───────────────────────────────────


class PublicationCampaign(Base):
    """Groups publication jobs for one listing version."""

    __tablename__ = "publication_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listing_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="job_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=JobStatus.pending_approval,
    )
    auto_distribute: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    account_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="publication_campaigns")
    listing: Mapped[Listing] = relationship()
    listing_version: Mapped[ListingVersion | None] = relationship()
    jobs: Mapped[list["PublicationJob"]] = relationship(
        back_populates="campaign", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PublicationCampaign {self.id}>"


class PublicationJob(Base):
    """One publication job targeting one social account."""

    __tablename__ = "publication_jobs"
    __table_args__ = (
        Index("ix_pub_jobs_campaign_status", "campaign_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="job_status_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=JobStatus.pending_approval,
    )
    rendered_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    content_items: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=None)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    campaign: Mapped[PublicationCampaign] = relationship(back_populates="jobs")
    social_account: Mapped[SocialAccount] = relationship()
    template: Mapped[ContentTemplate | None] = relationship()
    attempts: Mapped[list["PublicationAttempt"]] = relationship(
        back_populates="job", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PublicationJob {self.id} {self.status.value}>"


class PublicationAttempt(Base):
    """Immutable log of a single publish attempt."""

    __tablename__ = "publication_attempts"
    __table_args__ = (
        Index("ix_pub_attempts_job_created", "job_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(
            AttemptStatus,
            name="attempt_status_enum",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    job: Mapped[PublicationJob] = relationship(back_populates="attempts")

    def __repr__(self) -> str:
        return f"<PublicationAttempt {self.id}#{self.attempt_number}>"


class PublicationOutbox(Base):
    """Transactional outbox for publication events."""

    __tablename__ = "publication_outbox"
    __table_args__ = (
        Index("ix_pub_outbox_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TemplateVersion(Base):
    """Immutable prior version of a content template."""

    __tablename__ = "template_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    template: Mapped[ContentTemplate] = relationship(back_populates="template_versions")

    def __repr__(self) -> str:
        return f"<TemplateVersion {self.template_id}#{self.version}>"
