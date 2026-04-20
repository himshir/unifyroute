"""Rules engine (Brain v2) - User-facing rule pipeline for routing decisions

Phase 2: Replaces single-purpose brain with configurable rules engine.
"""

from .schema import (
    RoutingRule,
    RuleMatch,
    RuleAction,
    RuleEvalResult,
)
from .context import RequestContext, build_request_context
from .evaluator import RuleEvaluator, evaluate_predicate
from .pipeline import RulesPipeline

__all__ = [
    'RoutingRule',
    'RuleMatch',
    'RuleAction',
    'RuleEvalResult',
    'RequestContext',
    'build_request_context',
    'RuleEvaluator',
    'evaluate_predicate',
    'RulesPipeline',
]
