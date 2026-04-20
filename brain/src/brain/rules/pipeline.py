"""Rules pipeline orchestrator"""

from typing import List, Optional
from uuid import UUID
import logging

from .schema import RoutingRule, RuleEvalResult, RuleAction
from .context import RequestContext
from .evaluator import RuleEvaluator

logger = logging.getLogger(__name__)


class RulesPipeline:
    """
    Orchestrates rule evaluation and applies the first matching rule.

    Rules are evaluated in priority order (lower priority number = evaluated first).
    Supports multiple modes: 'select' (pick tier/model), 'filter' (exclude candidates),
    'annotate' (add metadata without changing routing).
    """

    def __init__(self, rules: List[RoutingRule]):
        """Initialize pipeline with list of rules, sorted by priority"""
        self.rules = sorted([r for r in rules if r.enabled], key=lambda r: r.priority)
        self.evaluator = RuleEvaluator()

    def apply(self, context: RequestContext) -> RuleEvalResult:
        """
        Evaluate all rules in priority order and return the effective action.

        The first matching rule with stop_on_match=True (or any matching rule if multiple)
        defines the effective routing decision.
        """
        matching_rules: List[tuple[RoutingRule, RuleAction]] = []

        for rule in self.rules:
            # Check if rule scope applies to this client
            if not self._scope_applies(rule, context):
                continue

            # Evaluate rule predicate
            try:
                matched = self.evaluator.evaluate(rule.match, context)
            except Exception as e:
                logger.warning(f"Error evaluating rule {rule.id}: {e}")
                matched = False

            if matched:
                matching_rules.append((rule, rule.action))

                # Stop if rule has stop_on_match flag
                if rule.action.stop_on_match:
                    break

        # If no rules matched, return empty result
        if not matching_rules:
            return RuleEvalResult(matched=False, reason="No rules matched")

        # Merge actions from all matching rules (first rule wins for conflicting decisions)
        combined_action = self._merge_actions([action for _, action in matching_rules])
        first_rule, _ = matching_rules[0]

        return RuleEvalResult(
            rule_id=first_rule.id,
            rule_name=first_rule.name,
            matched=True,
            action_applied=combined_action,
            reason=f"Matched rule: {first_rule.name}",
            effective_tier=combined_action.route_tier,
            effective_model=combined_action.route_model,
            effective_strategy=combined_action.strategy,
            effective_filters=self._build_filters(combined_action),
            effective_limits=self._build_limits(combined_action),
        )

    def _scope_applies(self, rule: RoutingRule, context: RequestContext) -> bool:
        """Check if rule's scope applies to this request"""
        scope = rule.scope or {}

        # Check client_key_ids scope
        client_key_ids = scope.get('client_key_ids', [])
        if client_key_ids:
            if context.client_key_id is None or str(context.client_key_id) not in [str(k) for k in client_key_ids]:
                return False

        # Check tags scope
        rule_tags = scope.get('tags', [])
        if rule_tags:
            if not any(tag in context.client_key_tags for tag in rule_tags):
                return False

        return True

    def _merge_actions(self, actions: List[RuleAction]) -> RuleAction:
        """Merge multiple rule actions (first one wins on conflicts)"""
        merged = RuleAction()

        for action in actions:
            if action.mode and action.mode != 'annotate':
                merged.mode = action.mode

            if action.route_tier:
                merged.route_tier = action.route_tier

            if action.route_model:
                merged.route_model = action.route_model

            if action.prefer_providers:
                merged.prefer_providers = action.prefer_providers

            if action.exclude_providers:
                merged.exclude_providers = action.exclude_providers

            if action.require_features:
                merged.require_features = action.require_features

            if action.min_usd_remaining is not None:
                merged.min_usd_remaining = action.min_usd_remaining

            if action.min_tokens_remaining is not None:
                merged.min_tokens_remaining = action.min_tokens_remaining

            if action.max_cost_usd is not None:
                merged.max_cost_usd = action.max_cost_usd

            if action.strategy:
                merged.strategy = action.strategy

            if action.set_tags:
                merged.set_tags = action.set_tags

        return merged

    def _build_filters(self, action: RuleAction) -> dict:
        """Build candidate filter dict from action"""
        filters = {}

        if action.exclude_providers:
            filters['exclude_providers'] = action.exclude_providers

        if action.prefer_providers:
            filters['prefer_providers'] = action.prefer_providers

        if action.require_features:
            filters['require_features'] = action.require_features

        return filters

    def _build_limits(self, action: RuleAction) -> dict:
        """Build limits dict from action"""
        limits = {}

        if action.min_tokens_remaining is not None:
            limits['min_tokens_remaining'] = action.min_tokens_remaining

        if action.min_usd_remaining is not None:
            limits['min_usd_remaining'] = action.min_usd_remaining

        if action.max_cost_usd is not None:
            limits['max_cost_usd'] = action.max_cost_usd

        return limits
