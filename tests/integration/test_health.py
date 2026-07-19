"""Integration tests for health and readiness endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadinessEndpoint:
    async def test_readiness_returns_ok(self, client: AsyncClient):
        response = await client.get("/api/v1/readiness")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        # database should be True since we're using a test DB
        assert data["checks"]["database"] is True
