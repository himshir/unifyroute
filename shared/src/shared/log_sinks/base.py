"""Base classes for log sinks"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEvent:
    """Structured log event"""
    timestamp: datetime
    level: LogLevel
    component: str
    event_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    client_key_id: Optional[str] = None


@dataclass
class SinkConfig:
    """Configuration for a log sink"""
    type: str
    enabled: bool = True
    levels: Optional[List[str]] = None  # Filter by level (default: all)
    component_filter: Optional[List[str]] = None  # Filter by component
    event_type_filter: Optional[List[str]] = None  # Filter by event type

    def matches_event(self, event: LogEvent) -> bool:
        """Check if event should be sent to this sink"""
        if not self.enabled:
            return False

        if self.levels and event.level.value not in self.levels:
            return False

        if self.component_filter and event.component not in self.component_filter:
            return False

        if self.event_type_filter and event.event_type not in self.event_type_filter:
            return False

        return True


class LogSink(ABC):
    """Base class for log sinks"""

    def __init__(self, config: SinkConfig):
        self.config = config

    @abstractmethod
    async def send(self, event: LogEvent) -> bool:
        """
        Send event to external system.

        Returns True on success, False on failure.
        Should not raise exceptions - failures are logged but don't block.
        """
        pass

    async def handle_event(self, event: LogEvent) -> bool:
        """Check filtering and send event"""
        if not self.config.matches_event(event):
            return False

        return await self.send(event)

    def close(self) -> None:
        """Clean up resources (optional)"""
        pass
