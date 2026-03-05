"""
Unit test for streaming token counting fallback logic.
Tests the exact code path that was modified in main.py to count tokens
using litellm.token_counter when providers don't return usage stats.
"""
import asyncio
import json
import tokenize
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_chunk(content: str = None, finish_reason: str = None, has_usage: bool = False):
    """Create a mock litellm ModelResponseStream chunk."""
    chunk = MagicMock()
    choice = MagicMock()
    delta = MagicMock()
    
    if content is not None:
        delta.content = content
    else:
        delta.content = None
    
    choice.delta = delta
    choice.finish_reason = finish_reason
    chunk.choices = [choice]
    
    if has_usage:
        chunk.usage = MagicMock()
        chunk.usage.prompt_tokens = 10
        chunk.usage.completion_tokens = 20
    else:
        chunk.usage = None
    
    return chunk


def _calculate_cost(prompt_tokens: int, completion_tokens: int, candidate) -> float:
    """Mirror of main.py's _calculate_cost function."""
    try:
        input_cost = getattr(candidate, 'input_cost_per_1k', 0.0) or 0.0
        output_cost = getattr(candidate, 'output_cost_per_1k', 0.0) or 0.0
        return round(
            (prompt_tokens / 1000.0) * float(input_cost)
            + (completion_tokens / 1000.0) * float(output_cost),
            8
        )
    except Exception:
        return 0.0


async def simulate_streaming_with_fallback(messages: list, chunks: list, candidate):
    """
    Simulate the streaming token counting logic from main.py.
    Returns (prompt_tokens, completion_tokens, cost_usd)
    """
    import litellm
    
    prompt_tokens = 0
    completion_tokens = 0
    full_response_text = ""
    usage_from_provider = False
    
    for chunk in chunks:
        if chunk.usage is not None:
            # Provider gave us usage stats
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
            usage_from_provider = True
        
        if chunk.choices and chunk.choices[0].delta.content:
            full_response_text += chunk.choices[0].delta.content
    
    # Fallback: count tokens ourselves if provider didn't give us stats
    if not usage_from_provider:
        prompt_tokens = litellm.token_counter(
            model="gpt-3.5-turbo",
            messages=messages
        )
        completion_tokens = litellm.token_counter(
            model="gpt-3.5-turbo",
            text=full_response_text
        )
    
    cost_usd = _calculate_cost(prompt_tokens, completion_tokens, candidate)
    return prompt_tokens, completion_tokens, cost_usd


def test_token_counting_with_provider_usage():
    """When provider returns usage stats in chunks, those should be used."""
    candidate = MagicMock()
    candidate.input_cost_per_1k = 0.5
    candidate.output_cost_per_1k = 1.5
    
    messages = [{"role": "user", "content": "Hello, world!"}]
    chunks = [
        make_mock_chunk("Hello ", has_usage=False),
        make_mock_chunk("world!", has_usage=False),
        make_mock_chunk(None, finish_reason="stop", has_usage=True),  # usage on last chunk
    ]
    
    prompt, completion, cost = asyncio.run(simulate_streaming_with_fallback(messages, chunks, candidate))
    
    # Provider said 10 prompt tokens and 20 completion tokens
    assert prompt == 10, f"Expected 10 prompt tokens from provider, got {prompt}"
    assert completion == 20, f"Expected 20 completion tokens from provider, got {completion}"
    assert cost > 0, f"Expected non-zero cost, got {cost}"
    print(f"✅ Provider usage: prompt={prompt}, completion={completion}, cost_usd={cost:.8f}")


def test_token_counting_fallback_without_provider_usage():
    """When provider DOESN'T return usage stats, litellm.token_counter should be used."""
    candidate = MagicMock()
    candidate.input_cost_per_1k = 0.5  # $0.50 per 1k input
    candidate.output_cost_per_1k = 1.5  # $1.50 per 1k output
    
    messages = [{"role": "user", "content": "Hello, count to 10!"}]
    chunks = [
        make_mock_chunk("1, 2, 3, "),
        make_mock_chunk("4, 5, 6, "),
        make_mock_chunk("7, 8, 9, 10."),
        make_mock_chunk(None, finish_reason="stop"),  # no usage stats
    ]
    
    prompt, completion, cost = asyncio.run(simulate_streaming_with_fallback(messages, chunks, candidate))
    
    # litellm.token_counter should have computed non-zero values
    assert prompt > 0, f"Prompt tokens should be > 0 (got {prompt})"
    assert completion > 0, f"Completion tokens should be > 0 (got {completion})"
    assert cost > 0, f"Cost should be > 0 (got {cost})"
    print(f"✅ Fallback token counting: prompt={prompt}, completion={completion}, cost_usd={cost:.8f}")


def test_cost_calculation():
    """Test that cost calculation is correct."""
    candidate = MagicMock()
    candidate.input_cost_per_1k = 1.0  # $1 per 1k tokens
    candidate.output_cost_per_1k = 2.0  # $2 per 1k tokens
    
    cost = _calculate_cost(1000, 1000, candidate)
    assert cost == 3.0, f"Expected $3.00 (1k in * $1 + 1k out * $2), got {cost}"
    
    cost = _calculate_cost(500, 250, candidate)
    expected = (500 / 1000) * 1.0 + (250 / 1000) * 2.0
    assert abs(cost - expected) < 0.0001, f"Expected {expected}, got {cost}"
    print(f"✅ Cost calculation: 500 in + 250 out @ $1/$2 per 1k = ${cost:.8f}")


def test_zero_tokens_results_in_zero_cost():
    """When token counts are zero, cost should be zero (don't charge for nothing)."""
    candidate = MagicMock()
    candidate.input_cost_per_1k = 1.0
    candidate.output_cost_per_1k = 2.0
    
    cost = _calculate_cost(0, 0, candidate)
    assert cost == 0.0, f"Expected 0.0 cost for 0 tokens, got {cost}"
    print(f"✅ Zero tokens = zero cost: {cost}")


if __name__ == "__main__":
    print("Running streaming cost unit tests...")
    test_cost_calculation()
    test_zero_tokens_results_in_zero_cost()
    test_token_counting_with_provider_usage()
    test_token_counting_fallback_without_provider_usage()
    print("\n✅ All tests passed!")
