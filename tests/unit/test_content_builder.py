"""Unit tests for content builder service."""

from unittest.mock import MagicMock

import pytest

from app.models import Listing, ListingStatus, PropertyType, TransactionType
from app.services.content_builder import build_variables


def test_build_variables_includes_title():
    listing = MagicMock(spec=Listing)
    listing.title = "Beautiful Apartment"
    listing.slug = "beautiful-apartment"
    listing.price = 500000
    listing.currency = "USD"
    listing.transaction_type = TransactionType.sale
    listing.property_type = PropertyType.apartment
    listing.listing_status = ListingStatus.published
    listing.bedrooms = 3
    listing.bathrooms = 2
    listing.balconies = 1
    listing.parking_spaces = 1
    listing.area = 1500
    listing.area_unit = "sqft"
    listing.furnishing_status = None
    listing.construction_status = None
    listing.ownership_type = None
    listing.floor_number = 5
    listing.total_floors = 10
    listing.address_line = "123 Main St"
    listing.locality = "Downtown"
    listing.city = "New York"
    listing.state_region = "NY"
    listing.postal_code = "10001"
    listing.country = "USA"
    listing.latitude = 40.7128
    listing.longitude = -74.0060
    listing.summary = "A beautiful apartment"
    listing.description = "Full description"
    listing.key_selling_points = ["Great view", "New kitchen"]
    listing.nearby_landmarks = ["Central Park", "Times Square"]
    listing.contact_name = "John Doe"
    listing.contact_phone = "+1234567890"
    listing.contact_email = "john@example.com"
    listing.whatsapp_contact = "+1234567890"
    listing.published_at = None
    listing.expires_at = None
    listing.updated_at = None
    listing.auto_distribute = False
    listing.version = 1
    listing.seo_title = None
    listing.meta_description = None
    listing.og_title = None
    listing.og_description = None
    listing.og_image_url = None
    listing.media = []

    vars = build_variables(listing)

    assert vars["title"] == "Beautiful Apartment"
    assert "Beautiful Apartment" in vars["title"]
    assert vars["slug"] == "beautiful-apartment"


def test_build_variables_price_formatted():
    listing = MagicMock(spec=Listing)
    listing.price = 500000
    listing.currency = "USD"
    listing.transaction_type = TransactionType.sale
    listing.property_type = PropertyType.apartment
    listing.listing_status = ListingStatus.draft
    listing.bedrooms = None
    listing.bathrooms = None
    listing.balconies = None
    listing.parking_spaces = None
    listing.area = None
    listing.area_unit = "sqft"
    listing.furnishing_status = None
    listing.construction_status = None
    listing.ownership_type = None
    listing.floor_number = None
    listing.total_floors = None
    listing.address_line = None
    listing.locality = None
    listing.city = "NYC"
    listing.state_region = None
    listing.postal_code = None
    listing.country = "USA"
    listing.latitude = None
    listing.longitude = None
    listing.summary = None
    listing.description = None
    listing.key_selling_points = None
    listing.nearby_landmarks = None
    listing.contact_name = None
    listing.contact_phone = None
    listing.contact_email = None
    listing.whatsapp_contact = None
    listing.published_at = None
    listing.expires_at = None
    listing.updated_at = None
    listing.auto_distribute = False
    listing.version = 1
    listing.seo_title = None
    listing.meta_description = None
    listing.og_title = None
    listing.og_description = None
    listing.og_image_url = None
    listing.media = []

    vars = build_variables(listing)

    assert vars["price_formatted"] == "USD 500,000"
    assert not vars["price_on_request"]


def test_build_variables_price_on_request():
    listing = MagicMock(spec=Listing)
    listing.price = None
    listing.currency = "USD"
    listing.transaction_type = TransactionType.rent
    listing.property_type = PropertyType.apartment
    listing.listing_status = ListingStatus.draft
    listing.bedrooms = None
    listing.bathrooms = None
    listing.balconies = None
    listing.parking_spaces = None
    listing.area = None
    listing.area_unit = "sqft"
    listing.furnishing_status = None
    listing.construction_status = None
    listing.ownership_type = None
    listing.floor_number = None
    listing.total_floors = None
    listing.address_line = None
    listing.locality = None
    listing.city = "NYC"
    listing.state_region = None
    listing.postal_code = None
    listing.country = "USA"
    listing.latitude = None
    listing.longitude = None
    listing.summary = None
    listing.description = None
    listing.key_selling_points = None
    listing.nearby_landmarks = None
    listing.contact_name = None
    listing.contact_phone = None
    listing.contact_email = None
    listing.whatsapp_contact = None
    listing.published_at = None
    listing.expires_at = None
    listing.updated_at = None
    listing.auto_distribute = False
    listing.version = 1
    listing.seo_title = None
    listing.meta_description = None
    listing.og_title = None
    listing.og_description = None
    listing.og_image_url = None
    listing.media = []

    vars = build_variables(listing)

    assert vars["price_formatted"] == ""
    assert vars["price_on_request"]


def test_build_variables_public_url():
    listing = MagicMock(spec=Listing)
    listing.slug = "my-property"
    listing.title = "My Property"
    listing.price = 100000
    listing.currency = "USD"
    listing.transaction_type = TransactionType.sale
    listing.property_type = PropertyType.house
    listing.listing_status = ListingStatus.draft
    listing.bedrooms = None
    listing.bathrooms = None
    listing.balconies = None
    listing.parking_spaces = None
    listing.area = None
    listing.area_unit = "sqft"
    listing.furnishing_status = None
    listing.construction_status = None
    listing.ownership_type = None
    listing.floor_number = None
    listing.total_floors = None
    listing.address_line = None
    listing.locality = None
    listing.city = ""
    listing.state_region = None
    listing.postal_code = None
    listing.country = ""
    listing.latitude = None
    listing.longitude = None
    listing.summary = None
    listing.description = None
    listing.key_selling_points = None
    listing.nearby_landmarks = None
    listing.contact_name = None
    listing.contact_phone = None
    listing.contact_email = None
    listing.whatsapp_contact = None
    listing.published_at = None
    listing.expires_at = None
    listing.updated_at = None
    listing.auto_distribute = False
    listing.version = 1
    listing.seo_title = None
    listing.meta_description = None
    listing.og_title = None
    listing.og_description = None
    listing.og_image_url = None
    listing.media = []

    vars = build_variables(listing)

    assert "/listings/my-property" in vars["public_url"]
