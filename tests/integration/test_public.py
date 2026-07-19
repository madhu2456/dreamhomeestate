"""Integration tests for public listings endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ListingStatus
from app.repositories.listing import ListingRepository
from datetime import datetime, timezone


class TestPublicListings:
    async def test_only_published_appear(
        self, authenticated_client: AsyncClient, db: AsyncSession, test_org
    ):
        """Only published listings should appear in public list."""
        repo = ListingRepository(db)

        # Create a published listing
        published = await repo.create(
            org_id=test_org.id,
            title="Published Property",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
            listing_status=ListingStatus.published,
            published_at=datetime.now(timezone.utc),
        )
        await db.flush()

        # Create a draft listing
        await repo.create(
            org_id=test_org.id,
            title="Draft Property",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
            listing_status=ListingStatus.draft,
        )
        await db.flush()

        # Public endpoint should only show published
        response = await authenticated_client.get("/api/v1/public/listings")
        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data]
        assert "Published Property" in titles
        assert "Draft Property" not in titles

    async def test_get_public_detail(
        self, authenticated_client: AsyncClient, db: AsyncSession, test_org
    ):
        """Get a single published listing detail."""
        repo = ListingRepository(db)

        listing = await repo.create(
            org_id=test_org.id,
            title="Public Detail Test",
            transaction_type="sale",
            property_type="house",
            city="Bangalore",
            country="India",
            listing_status=ListingStatus.published,
            published_at=datetime.now(timezone.utc),
        )
        await db.flush()

        response = await authenticated_client.get(
            f"/api/v1/public/listings/{listing.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Public Detail Test"
        assert data["slug"] is not None

    async def test_draft_not_found_public(
        self, authenticated_client: AsyncClient, db: AsyncSession, test_org
    ):
        """Draft listing should 404 from public endpoint."""
        repo = ListingRepository(db)

        listing = await repo.create(
            org_id=test_org.id,
            title="Draft Hidden",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
            listing_status=ListingStatus.draft,
        )
        await db.flush()

        response = await authenticated_client.get(
            f"/api/v1/public/listings/{listing.id}"
        )
        assert response.status_code == 404

    async def test_public_listings_with_filters(
        self, authenticated_client: AsyncClient, db: AsyncSession, test_org
    ):
        """Test public listing filters."""
        repo = ListingRepository(db)

        await repo.create(
            org_id=test_org.id,
            title="Cheap Apartment",
            transaction_type="sale",
            property_type="apartment",
            city="Mumbai",
            country="India",
            price=100000,
            listing_status=ListingStatus.published,
            published_at=datetime.now(timezone.utc),
        )
        await db.flush()

        await repo.create(
            org_id=test_org.id,
            title="Expensive House",
            transaction_type="sale",
            property_type="house",
            city="Delhi",
            country="India",
            price=5000000,
            listing_status=ListingStatus.published,
            published_at=datetime.now(timezone.utc),
        )
        await db.flush()

        # Filter by city
        resp = await authenticated_client.get(
            "/api/v1/public/listings", params={"city": "Mumbai"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all("Mumbai" in item["city"] for item in data)

        # Filter by property_type
        resp = await authenticated_client.get(
            "/api/v1/public/listings", params={"property_type": "house"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["property_type"] == "house" for item in data)

        # Filter by min_price
        resp = await authenticated_client.get(
            "/api/v1/public/listings", params={"min_price": 2000000}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["price"] >= 2000000 for item in data)
