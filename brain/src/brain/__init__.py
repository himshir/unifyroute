"""LLMWay Brain — internal provider/model management for the LLMWay system.

This module is NOT for routing end-user requests. It manages:
- Which providers/credentials/models the LLMWay system itself uses
- Health checking of those providers
- Bulk import of providers and credentials
- Ranking/selection of the best available provider for system use
"""
from .config import BrainProviderEntry
from .health import HealthResult, check_provider_health
from .ranker import RankedEntry, rank_brain_providers
from .selector import BrainSelection, select_for_brain
from .errors import brain_safe_message

__all__ = [
    "BrainProviderEntry",
    "HealthResult",
    "test_provider_health",
    "RankedEntry",
    "rank_brain_providers",
    "BrainSelection",
    "select_for_brain",
    "brain_safe_message",
]
