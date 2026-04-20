"""Pydantic schema definitions for rules engine"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union, Literal
from uuid import UUID


class RuleMatch(BaseModel):
    """Predicate tree for rule matching"""
    all: Optional[List['RuleMatch']] = None
    any: Optional[List['RuleMatch']] = None
    field: Optional[str] = None
    op: Optional[str] = None
    value: Optional[Any] = None

    class Config:
        extra = 'allow'


RuleMatch.update_forward_refs()


class RuleAction(BaseModel):
    """Action shape for matched rule"""
    mode: Literal['select', 'filter', 'annotate'] = 'select'
    route_tier: Optional[str] = None
    route_model: Optional[str] = None
    prefer_providers: Optional[List[str]] = None
    exclude_providers: Optional[List[str]] = None
    require_features: Optional[List[str]] = None
    min_usd_remaining: Optional[float] = None
    min_tokens_remaining: Optional[int] = None
    max_cost_usd: Optional[float] = None
    strategy: Optional[str] = None
    set_tags: Optional[List[str]] = None
    stop_on_match: bool = False


class RoutingRule(BaseModel):
    """User-defined routing rule (from DB)"""
    id: UUID
    name: str
    description: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    match: Dict[str, Any]
    action: RuleAction
    scope: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class RuleEvalResult(BaseModel):
    """Result of rule evaluation"""
    rule_id: Optional[UUID] = None
    rule_name: Optional[str] = None
    matched: bool = False
    action_applied: Optional[RuleAction] = None
    reason: Optional[str] = None

    # Combined effective routing decisions
    effective_tier: Optional[str] = None
    effective_model: Optional[str] = None
    effective_strategy: Optional[str] = None
    effective_filters: Dict[str, Any] = Field(default_factory=dict)
    effective_limits: Dict[str, Any] = Field(default_factory=dict)
