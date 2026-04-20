"""Log sink manager - orchestrates all sinks with fire-and-forget queue"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import LogSink, LogEvent, SinkConfig, LogLevel
from .syslog_sink import SyslogSink
from .otlp_sink import OTLPSink
from .loki_sink import LokiSink
from .webhook_sink import WebhookSink


logger = logging.getLogger(__name__)


class LogSinkManager:
    """
    Manages multiple log sinks with bounded queue and async draining.

    Fire-and-forget pattern: events are queued and sent asynchronously,
    failures don't block the request path.
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize manager.

        Args:
            max_queue_size: Maximum events in queue before dropping oldest
        """
        self.sinks: List[LogSink] = []
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size
        self.drainer_task: Optional[asyncio.Task] = None
        self.running = False

    def add_sink(self, sink: LogSink) -> None:
        """Add a sink"""
        self.sinks.append(sink)

    def add_syslog_sink(self, address: tuple = ('localhost', 514), **config_kwargs) -> None:
        """Add syslog sink"""
        config = SinkConfig(type='syslog', **config_kwargs)
        self.add_sink(SyslogSink(config, address=address))

    def add_otlp_sink(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **config_kwargs) -> None:
        """Add OTLP sink"""
        config = SinkConfig(type='otlp', **config_kwargs)
        self.add_sink(OTLPSink(config, endpoint=endpoint, headers=headers))

    def add_loki_sink(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **config_kwargs) -> None:
        """Add Loki sink"""
        config = SinkConfig(type='loki', **config_kwargs)
        self.add_sink(LokiSink(config, endpoint=endpoint, headers=headers))

    def add_webhook_sink(self, endpoint: str, headers: Optional[Dict[str, str]] = None, **config_kwargs) -> None:
        """Add webhook sink"""
        config = SinkConfig(type='webhook', **config_kwargs)
        self.add_sink(WebhookSink(config, endpoint=endpoint, headers=headers))

    async def start(self) -> None:
        """Start the drainer background task"""
        if self.running:
            return

        self.running = True
        self.drainer_task = asyncio.create_task(self._drain_queue())
        logger.info(f"Log sink manager started with {len(self.sinks)} sinks")

    async def stop(self) -> None:
        """Stop drainer and close all sinks"""
        if not self.running:
            return

        self.running = False

        # Wait for drainer to finish
        if self.drainer_task:
            try:
                await asyncio.wait_for(self.drainer_task, timeout=5)
            except asyncio.TimeoutError:
                self.drainer_task.cancel()

        # Close all sinks
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as e:
                logger.error(f"Error closing sink {sink.config.type}: {e}")

    def emit(self, event: LogEvent) -> None:
        """
        Emit a log event (fire-and-forget).

        Event is queued for async delivery. If queue is full, oldest event is dropped.
        """
        if not self.running:
            logger.debug("Log sink manager not running, dropping event")
            return

        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Queue is full, drop oldest event
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass

    async def _drain_queue(self) -> None:
        """Background task that continuously drains queue and sends to all sinks"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # Send to all sinks concurrently
                tasks = [
                    sink.handle_event(event)
                    for sink in self.sinks
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error in log sink drainer: {e}")

    def emit_system_event(
        self,
        level: str,
        component: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        client_key_id: Optional[str] = None,
    ) -> None:
        """
        Emit a system event.

        This is the main API for emitting structured system events.
        """
        try:
            log_level = LogLevel(level.upper())
        except ValueError:
            log_level = LogLevel.INFO

        event = LogEvent(
            timestamp=datetime.utcnow(),
            level=log_level,
            component=component,
            event_type=event_type,
            message=message,
            details=details,
            request_id=request_id,
            client_key_id=client_key_id,
        )

        self.emit(event)


# Global singleton instance
_manager: Optional[LogSinkManager] = None


def get_sink_manager() -> LogSinkManager:
    """Get global log sink manager"""
    global _manager
    if _manager is None:
        _manager = LogSinkManager()
    return _manager


async def configure_sinks_from_config(config: Dict[str, Any]) -> None:
    """Configure sinks from configuration dict"""
    manager = get_sink_manager()

    sinks_config = config.get('sinks', [])
    for sink_config in sinks_config:
        sink_type = sink_config.get('type')

        if sink_type == 'syslog':
            address = sink_config.get('address', ('localhost', 514))
            if isinstance(address, list):
                address = tuple(address)
            manager.add_syslog_sink(
                address=address,
                levels=sink_config.get('levels'),
                component_filter=sink_config.get('component_filter'),
            )

        elif sink_type == 'otlp':
            manager.add_otlp_sink(
                endpoint=sink_config.get('endpoint'),
                headers=sink_config.get('headers'),
                levels=sink_config.get('levels'),
                component_filter=sink_config.get('component_filter'),
            )

        elif sink_type == 'loki':
            manager.add_loki_sink(
                endpoint=sink_config.get('endpoint'),
                headers=sink_config.get('headers'),
                levels=sink_config.get('levels'),
                component_filter=sink_config.get('component_filter'),
            )

        elif sink_type == 'webhook':
            manager.add_webhook_sink(
                endpoint=sink_config.get('endpoint'),
                headers=sink_config.get('headers'),
                levels=sink_config.get('levels'),
                component_filter=sink_config.get('component_filter'),
            )

    if manager.sinks:
        await manager.start()
        logger.info(f"Configured {len(manager.sinks)} log sinks")
