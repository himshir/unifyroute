"""Brain selector — picks the best available provider/credential/model for system use.

Calls rank_brain_providers() and returns the top-ranked healthy entry.
If no healthy entry exists, falls back to any enabled entry (even unhealthy),
and if that also fails, returns a BrainSelection with ok=False and a clear message.

This output is consumed by internal LLMWay automation; it is never surfaced
directly to end-users.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .ranker import rank_brain_providers


@dataclass
class BrainSelection:
    ok: bool
    provider: str = ""
    credential_id: UUID | None = None
    credential_label: str = ""
    model_id: str = ""
    score: float = 0.0
    reason: str = ""


async def select_for_brain(session: AsyncSession) -> BrainSelection:
    """Select the single best provider/credential/model for internal system use.

    Selection order:
      1. Highest-scored healthy (health_ok=True) entry
      2. If none healthy: highest-scored entry regardless of health
      3. If no entries at all: returns ok=False with an explanatory message
    """
    ranked = await rank_brain_providers(session)

    if not ranked:
        return BrainSelection(
            ok=False,
            reason=(
                "No brain providers are configured. "
                "Use POST /admin/brain/providers or POST /admin/brain/import to add some."
            ),
        )

    # Prefer a healthy entry
    healthy = [e for e in ranked if e.health_ok]
    best = healthy[0] if healthy else ranked[0]

    if best.health_ok:
        reason = f"Selected by score {best.score:.3f} (healthy)"
    else:
        reason = (
            f"Selected by score {best.score:.3f} (no healthy providers available; "
            f"last health message: {best.health_message})"
        )

    return BrainSelection(
        ok=best.health_ok,
        provider=best.provider,
        credential_id=best.credential_id,
        credential_label=best.credential_label,
        model_id=best.model_id,
        score=best.score,
        reason=reason,
    )
