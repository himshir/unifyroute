"""Grafana Loki sink implementation"""

import aiohttp
import json
from typing import Optional, Dict, Any
import logging

from .base import LogSink, LogEvent, SinkConfig


logger = logging.getLogger(__name__)


class LokiSink(LogSink):
    """Sends logs to Grafana Loki"""

    def __init__(self, config: SinkConfig, endpoint: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize Loki sink.

        Args:
            config: Sink configuration
            endpoint: Loki HTTP endpoint (e.g., http://loki:3100)
            headers: Optional HTTP headers (e.g., authorization)
        """
        super().__init__(config)
        self.endpoint = endpoint.rstrip('/')
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazy-initialize HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send(self, event: LogEvent) -> bool:
        """Send event to Loki"""
        try:
            session = await self._ensure_session()

            # Loki expects log entries as a list of [timestamp_ns, log_line]
            # Plus labels as key-value pairs
            timestamp_ns = int(event.timestamp.timestamp() * 1e9)
            log_line = self._format_log_line(event)

            # Build Loki-compatible payload
            payload = {
                'streams': [
                    {
                        'stream': {
                            'component': event.component,
                            'level': event.level.value,
                            'event_type': event.event_type,
                        },
                        'values': [
                            [str(timestamp_ns), log_line]
                        ]
                    }
                ]
            }

            # Send to Loki
            async with session.post(
                f'{self.endpoint}/loki/api/v1/push',
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status in (200, 201, 202, 204)

        except Exception as e:
            logger.error(f"Failed to send to Loki: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    @staticmethod
    def _format_log_line(event: LogEvent) -> str:
        """Format event as JSON log line for Loki"""
        log_data = {
            'message': event.message,
            'event_type': event.event_type,
            'request_id': event.request_id,
            'client_key_id': event.client_key_id,
        }
        if event.details:
            log_data.update(event.details)

        return json.dumps(log_data)
