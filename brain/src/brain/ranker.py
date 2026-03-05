"""Brain ranker — scores and ranks provider/credential/model triples for Brain use.

Scoring factors (higher = better):

  Priority weight  (40%) — inverse of brain_config.priority (lower priority value → higher score)
  Health status    (30%) — 1.0 if last health check passed, 0.0 if failed or unknown
  Quota remaining  (20%) — normalised tokens_remaining from Redis (capped at 1M)
  Latency          (10%) — inverse of last latency_ms (lower latency → higher score, capped at 10 s)

All factors are normalised to [0, 1] before weighting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import BrainConfig

from .tester import get_cached_health


_W_PRIORITY = 0.40
_W_HEALTH =   0.30
_W_QUOTA =    0.20
_W_LATENCY =  0.10

_MAX_PRIORITY = 1000   # scores capped here for normalisation
_MAX_QUOTA =    1_000_000
_MAX_LATENCY =  10_000  # ms


@dataclass
class RankedEntry:
    brain_config_id: UUID
    provider: str
    credential_id: UUID
    credential_label: str
    model_id: str
    priority: int
    score: float           # composite score, higher = better
    health_ok: bool
    health_message: str
    latency_ms: int
    quota_remaining: int   # -1 if unknown


async def rank_brain_providers(session: AsyncSession) -> List[RankedEntry]:
    """Return all enabled brain configs sorted by composite ranking score (best first)."""
    stmt = (
        select(BrainConfig)
        .where(BrainConfig.enabled == True)
        .options(
            selectinload(BrainConfig.provider),
            selectinload(BrainConfig.credential),
        )
    )
    res = await session.execute(stmt)
    entries = res.scalars().all()

    ranked: List[RankedEntry] = []

    for entry in entries:
        # --- health score ---
        cached = await get_cached_health(entry.credential_id, entry.model_id)
        if cached:
            health_ok = cached.get("ok", False)
            latency_ms = int(cached.get("latency_ms", _MAX_LATENCY))
            health_message = cached.get("message", "")
            quota_remaining = -1  # not stored in health cache
        else:
            health_ok = False   # treat unknown as unhealthy; tester must run first
            latency_ms = _MAX_LATENCY
            health_message = "Not yet tested"
            quota_remaining = -1

        # --- quota from Redis ---
        try:
            import os
            import redis.asyncio as redis_async
            r = redis_async.from_url(
                os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
            q_key = f"quota:{entry.credential_id}:{entry.model_id}"
            q_val = await r.get(q_key)
            if q_val is not None:
                quota_remaining = int(q_val)
        except Exception:
            pass

        # --- composite score ---
        # Priority: lower number = higher priority → invert
        prio_norm = max(0.0, 1.0 - entry.priority / _MAX_PRIORITY)
        health_norm = 1.0 if health_ok else 0.0
        quota_norm = min(1.0, max(quota_remaining, 0) / _MAX_QUOTA) if quota_remaining >= 0 else 0.5
        latency_norm = max(0.0, 1.0 - min(latency_ms, _MAX_LATENCY) / _MAX_LATENCY)

        score = (
            _W_PRIORITY * prio_norm
            + _W_HEALTH   * health_norm
            + _W_QUOTA    * quota_norm
            + _W_LATENCY  * latency_norm
        )

        ranked.append(RankedEntry(
            brain_config_id=entry.id,
            provider=entry.provider.name,
            credential_id=entry.credential_id,
            credential_label=entry.credential.label,
            model_id=entry.model_id,
            priority=entry.priority,
            score=round(score, 4),
            health_ok=health_ok,
            health_message=health_message,
            latency_ms=latency_ms,
            quota_remaining=quota_remaining,
        ))

    ranked.sort(key=lambda x: -x.score)
    return ranked
