"""Brain tester — runs live health checks against all brain-assigned credentials.

Iterates every enabled BrainConfig entry, calls health.test_provider_health()
for each one, caches the result to Redis, and returns a summary list.
All per-credential failures are caught; one failure never stops the others.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models import BrainConfig
from shared.security import decrypt_secret

from .health import HealthResult, check_provider_health
from .errors import brain_safe_message


@dataclass
class TestResult:
    brain_config_id: UUID
    provider: str
    credential_label: str
    credential_id: UUID
    model_id: str
    ok: bool
    message: str
    latency_ms: int
    tested_at: float  # unix timestamp


def _get_redis():
    """Lazy Redis connection (same config as router)."""
    import os
    import redis.asyncio as redis_async
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_async.from_url(url, decode_responses=True)


async def _cache_health(credential_id: UUID, model_id: str, health: HealthResult) -> None:
    """Store the health result in Redis for use by the ranker."""
    try:
        r = _get_redis()
        key = f"brain:health:{credential_id}:{model_id}"
        payload = json.dumps({
            "ok": health.ok,
            "latency_ms": health.latency_ms,
            "message": health.message,
            "status_code": health.status_code,
            "tested_at": time.time(),
        })
        await r.setex(key, 300, payload)  # cache for 5 min
    except Exception:
        pass  # Redis unavailable — continue without caching


async def get_cached_health(credential_id: UUID, model_id: str) -> dict | None:
    """Retrieve the last cached health result from Redis."""
    try:
        r = _get_redis()
        key = f"brain:health:{credential_id}:{model_id}"
        val = await r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


async def test_all_brain_credentials(session: AsyncSession) -> List[TestResult]:
    """Test every enabled brain credential and return results.

    Each credential is tested independently — one failure does not abort others.
    Results are cached in Redis for use by the ranker.
    """
    stmt = (
        select(BrainConfig)
        .where(BrainConfig.enabled == True)
        .options(
            selectinload(BrainConfig.provider),
            selectinload(BrainConfig.credential),
        )
        .order_by(BrainConfig.priority)
    )
    res = await session.execute(stmt)
    entries = res.scalars().all()

    results: List[TestResult] = []

    for entry in entries:
        try:
            api_key = decrypt_secret(entry.credential.secret_enc, entry.credential.iv)
            base_url = entry.provider.base_url or None
            health = await check_provider_health(
                provider_name=entry.provider.name,
                api_key=api_key,
                base_url=base_url,
            )
        except Exception as exc:
            health = HealthResult(ok=False, message=brain_safe_message(exc))

        # Cache to Redis
        await _cache_health(entry.credential_id, entry.model_id, health)

        results.append(TestResult(
            brain_config_id=entry.id,
            provider=entry.provider.name,
            credential_label=entry.credential.label,
            credential_id=entry.credential_id,
            model_id=entry.model_id,
            ok=health.ok,
            message=health.message,
            latency_ms=health.latency_ms,
            tested_at=time.time(),
        ))

    return results
