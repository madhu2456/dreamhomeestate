"""Listing schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import (
    ConstructionStatus,
    FurnishingStatus,
    ListingStatus,
    OwnershipType,
    PropertyType,
    TransactionType,
)


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    transaction_type: TransactionType
    property_type: PropertyType
    city: str = Field(default="", max_length=100)
    country: str = Field(default="", max_length=100)

    listing_status: ListingStatus = ListingStatus.draft
    price: int | None = None
    currency: str = "USD"
    negotiable: bool = False
    deposit: int | None = None
    maintenance_charges: int | None = None

    area: int | None = None
    area_unit: str = "sqft"
    bedrooms: int | None = None
    bathrooms: int | None = None
    balconies: int | None = None
    parking_spaces: int | None = None
    furnishing_status: FurnishingStatus | None = None
    construction_status: ConstructionStatus | None = None
    ownership_type: OwnershipType | None = None
    floor_number: int | None = None
    total_floors: int | None = None

    address_line: str | None = None
    locality: str | None = None
    landmark: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    summary: str | None = None
    description: str | None = None
    key_selling_points: list[str] | None = None
    nearby_landmarks: list[str] | None = None

    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    whatsapp_contact: str | None = None

    seo_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image_url: str | None = None

    auto_distribute: bool = False
    expires_at: datetime | None = None


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    transaction_type: TransactionType | None = None
    property_type: PropertyType | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)

    listing_status: ListingStatus | None = None
    price: int | None = None
    currency: str | None = None
    negotiable: bool | None = None
    deposit: int | None = None
    maintenance_charges: int | None = None

    area: int | None = None
    area_unit: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    balconies: int | None = None
    parking_spaces: int | None = None
    furnishing_status: FurnishingStatus | None = None
    construction_status: ConstructionStatus | None = None
    ownership_type: OwnershipType | None = None
    floor_number: int | None = None
    total_floors: int | None = None

    address_line: str | None = None
    locality: str | None = None
    landmark: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    summary: str | None = None
    description: str | None = None
    key_selling_points: list[str] | None = None
    nearby_landmarks: list[str] | None = None

    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    whatsapp_contact: str | None = None

    seo_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image_url: str | None = None

    auto_distribute: bool | None = None
    expires_at: datetime | None = None


class MediaOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    kind: str
    url: str | None = None
    variants: dict | None = None
    width: int | None = None
    height: int | None = None
    order_index: int
    is_cover: bool
    processing_status: str
    caption: str | None = None
    original_file_name: str | None = None

    model_config = {"from_attributes": True}


class ListingOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID = Field(validation_alias="organization_id")
    slug: str
    listing_status: ListingStatus

    title: str
    transaction_type: TransactionType
    property_type: PropertyType
    price: int | None = None
    currency: str
    negotiable: bool
    deposit: int | None = None
    maintenance_charges: int | None = None

    area: int | None = None
    area_unit: str
    bedrooms: int | None = None
    bathrooms: int | None = None
    balconies: int | None = None
    parking_spaces: int | None = None
    furnishing_status: FurnishingStatus | None = None
    construction_status: ConstructionStatus | None = None
    ownership_type: OwnershipType | None = None
    floor_number: int | None = None
    total_floors: int | None = None

    address_line: str | None = None
    locality: str | None = None
    landmark: str | None = None
    city: str
    state_region: str | None = None
    postal_code: str | None = None
    country: str
    latitude: float | None = None
    longitude: float | None = None

    summary: str | None = None
    description: str | None = None
    key_selling_points: list[str] | None = None
    nearby_landmarks: list[str] | None = None

    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    whatsapp_contact: str | None = None

    seo_title: str | None = None
    meta_description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image_url: str | None = None

    auto_distribute: bool
    version: int

    published_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    media: list[MediaOut] = []

    model_config = {"from_attributes": True}


class PublicListingOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    transaction_type: TransactionType
    property_type: PropertyType
    price: int | None = None
    currency: str
    negotiable: bool
    area: int | None = None
    area_unit: str
    bedrooms: int | None = None
    bathrooms: int | None = None
    city: str
    state_region: str | None = None
    country: str
    summary: str | None = None
    description: str | None = None
    key_selling_points: list[str] | None = None
    published_at: datetime | None = None
    media: list[MediaOut] = []

    model_config = {"from_attributes": True}
