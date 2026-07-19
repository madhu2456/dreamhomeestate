"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])

settings = get_settings()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/readiness")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    checks: dict[str, bool] = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Redis check — best-effort
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(str(settings.redis_url), decode_responses=True)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
