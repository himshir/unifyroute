"""Request context builder for rule evaluation"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class RequestContext:
    """Complete context for evaluating rules on a request"""

    # Request properties
    model_alias: str
    messages_count: int = 0
    prompt_tokens_estimate: int = 0
    has_functions: bool = False
    has_tools: bool = False
    stream: bool = False
    temperature: float = 1.0

    # Client key properties
    client_key_id: Optional[UUID] = None
    client_key_tags: List[str] = field(default_factory=list)
    client_key_scopes: List[str] = field(default_factory=list)

    # Session properties
    session_id: Optional[str] = None
    conversation_length: int = 0

    # Time-based properties
    hour_of_day: int = 0
    day_of_week: int = 0

    # Credit properties
    credit: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # credit format: {"provider_name": {"tokens_remaining": 1000, "usd_remaining": 10.5, "unknown": False}}

    # Task classification
    task_type: Optional[str] = None

    @classmethod
    def build(cls, **kwargs) -> 'RequestContext':
        """Build context from kwargs, filling in defaults"""
        now = datetime.now()
        defaults = {
            'hour_of_day': now.hour,
            'day_of_week': now.weekday(),
        }
        defaults.update(kwargs)
        return cls(**defaults)

    def get_field(self, field_path: str) -> Any:
        """
        Get a field value using dot notation.

        Examples:
            'model_alias' -> str
            'client_key.tags' -> list
            'credit.anthropic.usd_remaining' -> float
            'hour_of_day' -> int
        """
        parts = field_path.split('.')
        current = self

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                try:
                    current = getattr(current, part, None)
                except AttributeError:
                    return None

            if current is None:
                return None

        return current

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for rule evaluation"""
        return {
            'model_alias': self.model_alias,
            'messages_count': self.messages_count,
            'prompt_tokens_estimate': self.prompt_tokens_estimate,
            'has_functions': self.has_functions,
            'has_tools': self.has_tools,
            'stream': self.stream,
            'temperature': self.temperature,
            'client_key': {
                'id': str(self.client_key_id) if self.client_key_id else None,
                'tags': self.client_key_tags,
                'scopes': self.client_key_scopes,
            },
            'session_id': self.session_id,
            'conversation_length': self.conversation_length,
            'hour_of_day': self.hour_of_day,
            'day_of_week': self.day_of_week,
            'credit': self.credit,
            'task_type': self.task_type,
        }


def build_request_context(
    model_alias: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    client_key_id: Optional[UUID] = None,
    client_key_tags: Optional[List[str]] = None,
    client_key_scopes: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    credit: Optional[Dict[str, Dict[str, Any]]] = None,
    task_type: Optional[str] = None,
    stream: bool = False,
    temperature: float = 1.0,
    **kwargs
) -> RequestContext:
    """
    Build a RequestContext from request parameters.

    This is the primary entry point for building context in the router.
    """
    # Count messages and estimate tokens (rough estimate)
    messages_count = len(messages) if messages else 0
    prompt_tokens_estimate = 0
    if messages:
        for msg in messages:
            content = msg.get('content', '')
            # Rough token estimate: 1 token ≈ 4 characters
            prompt_tokens_estimate += len(str(content)) // 4

    # Check for functions/tools
    has_functions = any(
        msg.get('tool_calls') or msg.get('function_call')
        for msg in (messages or [])
    )
    has_tools = has_functions  # For now, treat tools same as functions

    return RequestContext.build(
        model_alias=model_alias,
        messages_count=messages_count,
        prompt_tokens_estimate=prompt_tokens_estimate,
        has_functions=has_functions,
        has_tools=has_tools,
        stream=stream,
        temperature=temperature,
        client_key_id=client_key_id,
        client_key_tags=client_key_tags or [],
        client_key_scopes=client_key_scopes or [],
        session_id=session_id,
        credit=credit or {},
        task_type=task_type,
        **kwargs
    )
