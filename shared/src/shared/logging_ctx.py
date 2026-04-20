"""Structured logging context with correlation ID support (Phase 0)

This module provides context-aware logging with automatic propagation of
request_id (correlation ID) across services via contextvars.
"""

import contextvars
import logging
import json
from uuid import UUID, uuid4
from typing import Any, Dict, Optional
from datetime import datetime


# Context variable for storing request_id across async calls
request_id_context: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar('request_id', default=None)
client_key_context: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar('client_key', default=None)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects request_id into all log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = request_id_context.get()
        if request_id:
            record.request_id = str(request_id)
        else:
            record.request_id = None

        client_key = client_key_context.get()
        if client_key:
            record.client_key = str(client_key)
        else:
            record.client_key = None

        return True


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs with correlation IDs"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
        }

        # Add correlation ID if available
        if hasattr(record, 'request_id') and record.request_id:
            log_data['request_id'] = record.request_id

        if hasattr(record, 'client_key') and record.client_key:
            log_data['client_key'] = record.client_key

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        return json.dumps(log_data)


def set_request_context(request_id: Optional[UUID], client_key_id: Optional[UUID] = None) -> None:
    """Set the correlation ID and client key for the current request context"""
    if request_id is None:
        request_id = uuid4()
    request_id_context.set(request_id)
    if client_key_id:
        client_key_context.set(client_key_id)


def get_request_id() -> Optional[UUID]:
    """Get the current request_id from context"""
    return request_id_context.get()


def get_client_key() -> Optional[UUID]:
    """Get the current client_key from context"""
    return client_key_context.get()


def clear_request_context() -> None:
    """Clear the request context (e.g., at end of request)"""
    request_id_context.set(None)
    client_key_context.set(None)


def configure_structured_logging(logger: logging.Logger, json_format: bool = True) -> None:
    """Configure a logger with structured logging and correlation IDs"""
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    logger.addFilter(correlation_filter)

    # Create and configure handler
    handler = logging.StreamHandler()

    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Default logger with structured logging enabled
logger = logging.getLogger('unifyroute')
configure_structured_logging(logger)


def emit_system_event(
    level: str,
    component: str,
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> None:
    """
    Emit a structured system event with correlation ID.

    This is a helper that logs the event and will be persisted to SystemEvent
    table by the API layer after it reads from logs.
    """
    if logger_instance is None:
        logger_instance = logger

    log_level = getattr(logging, level.upper(), logging.INFO)
    request_id = get_request_id()

    extra_data = {
        'extra': {
            'component': component,
            'event_type': event_type,
            'request_id': str(request_id) if request_id else None,
        }
    }

    if details:
        extra_data['extra']['details'] = details

    logger_instance.log(log_level, f"[{component}] {event_type}: {message}", extra=extra_data.get('extra'))
