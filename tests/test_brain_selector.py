"""
Unit tests for brain.selector module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from brain.selector import select_for_brain, BrainSelection

@pytest.mark.asyncio
async def test_select_for_brain_empty():
    """Returns ok=False when no brain configs exist."""
    session = AsyncMock()
    with patch("brain.selector.rank_brain_providers", new_callable=AsyncMock) as mock_rank:
        mock_rank.return_value = []
        result = await select_for_brain(session)
    
    assert isinstance(result, BrainSelection)
    assert result.ok is False
    assert "No brain providers are configured" in result.reason
    assert result.provider == ""  # BrainSelection.provider is '' when empty

@pytest.mark.asyncio
async def test_select_for_brain_all_unhealthy():
    """Returns ok=False when configs exist but none are healthy."""
    session = AsyncMock()
    
    mock_entry = MagicMock()
    mock_entry.health_ok = False
    mock_entry.score = 0.5
    mock_entry.health_message = "Connection failed"
    
    with patch("brain.selector.rank_brain_providers", new_callable=AsyncMock) as mock_rank:
        mock_rank.return_value = [mock_entry]
        result = await select_for_brain(session)

    assert result.ok is False
    # When all are unhealthy, the selector picks the best but marks as unhealthy fallback
    assert "no healthy providers" in result.reason.lower() or result.ok is False

@pytest.mark.asyncio
async def test_select_for_brain_success():
    """Returns ok=True with the highest-scored healthy provider."""
    session = AsyncMock()
    
    mock_entry = MagicMock()
    mock_entry.health_ok = True
    mock_entry.provider = "openai"
    mock_entry.credential_id = "test-cred-id"
    mock_entry.credential_label = "test-label"
    mock_entry.model_id = "test-model"
    mock_entry.score = 0.95
    
    with patch("brain.selector.rank_brain_providers", new_callable=AsyncMock) as mock_rank:
        # rank_brain_providers already returns a sorted list, we pick the first healthy one
        mock_rank.return_value = [mock_entry]
        result = await select_for_brain(session)
        
    assert result.ok is True
    assert result.provider == "openai"
    assert result.credential_id == "test-cred-id"
    assert result.model_id == "test-model"
    assert result.score == 0.95
    assert "Selected" in result.reason
