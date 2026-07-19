"""Content builder — snapshot listing data and build canonical variable dict."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Listing, ListingVersion, Organization


def build_variables(listing: Listing) -> dict:
    settings = get_settings()
    variables: dict = {}

    variables["title"] = listing.title
    variables["slug"] = listing.slug
    variables["price"] = listing.price
    variables["currency"] = listing.currency
    if listing.price is not None:
        try:
            variables["price_formatted"] = f"{listing.currency} {listing.price:,}"
        except (ValueError, TypeError):
            variables["price_formatted"] = f"{listing.currency} {listing.price}"
    else:
        variables["price_formatted"] = ""
    variables["price_on_request"] = listing.price is None
    variables["transaction_type"] = listing.transaction_type.value if listing.transaction_type else ""
    variables["property_type"] = listing.property_type.value if listing.property_type else ""

    variables["bedrooms"] = listing.bedrooms
    variables["bathrooms"] = listing.bathrooms
    variables["balconies"] = listing.balconies
    variables["parking_spaces"] = listing.parking_spaces

    variables["area"] = listing.area
    variables["area_unit"] = listing.area_unit
    if listing.area is not None:
        try:
            variables["area_formatted"] = f"{listing.area:,} {listing.area_unit}"
        except (ValueError, TypeError):
            variables["area_formatted"] = f"{listing.area} {listing.area_unit}"
    else:
        variables["area_formatted"] = ""

    variables["furnishing_status"] = listing.furnishing_status.value if listing.furnishing_status else ""
    variables["construction_status"] = listing.construction_status.value if listing.construction_status else ""
    variables["ownership_type"] = listing.ownership_type.value if listing.ownership_type else ""
    variables["floor_number"] = listing.floor_number
    variables["total_floors"] = listing.total_floors

    variables["address_line"] = listing.address_line or ""
    variables["locality"] = listing.locality or ""
    variables["city"] = listing.city
    variables["state_region"] = listing.state_region or ""
    variables["postal_code"] = listing.postal_code or ""
    variables["country"] = listing.country

    variables["latitude"] = listing.latitude
    variables["longitude"] = listing.longitude

    variables["summary"] = listing.summary or ""
    variables["description"] = listing.description or ""
    variables["key_selling_points"] = listing.key_selling_points or []
    variables["nearby_landmarks"] = listing.nearby_landmarks or []

    variables["contact_name"] = listing.contact_name or ""
    variables["contact_phone"] = listing.contact_phone or ""
    variables["contact_email"] = listing.contact_email or ""
    variables["whatsapp_contact"] = listing.whatsapp_contact or ""

    variables["listing_status"] = listing.listing_status.value if listing.listing_status else ""

    base_url = settings.live_domain.rstrip("/")
    variables["public_url"] = f"{base_url}/listings/{listing.slug}"

    variables["published_at"] = listing.published_at.isoformat() if listing.published_at else ""
    variables["updated_at"] = listing.updated_at.isoformat() if listing.updated_at else ""

    return variables


async def snapshot_listing(db: AsyncSession, listing: Listing) -> ListingVersion:
    data = {
        "title": listing.title,
        "slug": listing.slug,
        "price": listing.price,
        "currency": listing.currency,
        "transaction_type": listing.transaction_type.value if listing.transaction_type else None,
        "property_type": listing.property_type.value if listing.property_type else None,
        "listing_status": listing.listing_status.value if listing.listing_status else None,
        "version": listing.version,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "balconies": listing.balconies,
        "parking_spaces": listing.parking_spaces,
        "area": listing.area,
        "area_unit": listing.area_unit,
        "furnishing_status": listing.furnishing_status.value if listing.furnishing_status else None,
        "construction_status": listing.construction_status.value if listing.construction_status else None,
        "ownership_type": listing.ownership_type.value if listing.ownership_type else None,
        "floor_number": listing.floor_number,
        "total_floors": listing.total_floors,
        "address_line": listing.address_line,
        "locality": listing.locality,
        "city": listing.city,
        "state_region": listing.state_region,
        "postal_code": listing.postal_code,
        "country": listing.country,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        "summary": listing.summary,
        "description": listing.description,
        "key_selling_points": listing.key_selling_points,
        "nearby_landmarks": listing.nearby_landmarks,
        "contact_name": listing.contact_name,
        "contact_phone": listing.contact_phone,
        "contact_email": listing.contact_email,
        "whatsapp_contact": listing.whatsapp_contact,
        "auto_distribute": listing.auto_distribute,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "expires_at": listing.expires_at.isoformat() if listing.expires_at else None,
        "seo_title": listing.seo_title,
        "meta_description": listing.meta_description,
        "og_title": listing.og_title,
        "og_description": listing.og_description,
        "og_image_url": listing.og_image_url,
    }

    if listing.media:
        media_data = []
        for m in listing.media:
            variants = m.variants or {}
            media_data.append({
                "id": str(m.id),
                "kind": m.kind.value if hasattr(m.kind, "value") else str(m.kind),
                "is_cover": m.is_cover,
                "order_index": m.order_index,
                "urls": {k: v for k, v in variants.items()},
            })
        data["media"] = media_data

    latest_version_number = listing.version
    result = await db.execute(
        select(ListingVersion)
        .where(ListingVersion.listing_id == listing.id)
        .order_by(ListingVersion.version_number.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    version_number = (existing.version_number + 1) if existing else 1

    listing_version = ListingVersion(
        listing_id=listing.id,
        version_number=version_number,
        data=data,
    )
    db.add(listing_version)
    await db.flush()
    await db.refresh(listing_version)
    return listing_version
