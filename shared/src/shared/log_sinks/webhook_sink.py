"""Generic HTTP webhook sink implementation"""

import aiohttp
import json
from typing import Optional, Dict, Any
import logging

from .base import LogSink, LogEvent, SinkConfig


logger = logging.getLogger(__name__)


class WebhookSink(LogSink):
    """Sends logs to generic HTTP webhook"""

    def __init__(self, config: SinkConfig, endpoint: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize webhook sink.

        Args:
            config: Sink configuration
            endpoint: HTTP endpoint URL
            headers: Optional HTTP headers (e.g., authorization, content-type)
        """
        super().__init__(config)
        self.endpoint = endpoint
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazy-initialize HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send(self, event: LogEvent) -> bool:
        """Send event to webhook"""
        try:
            session = await self._ensure_session()

            # Build generic JSON payload
            payload = {
                'timestamp': event.timestamp.isoformat(),
                'level': event.level.value,
                'component': event.component,
                'event_type': event.event_type,
                'message': event.message,
                'request_id': event.request_id,
                'client_key_id': event.client_key_id,
            }
            if event.details:
                payload['details'] = event.details

            # Set default content-type
            headers = {'Content-Type': 'application/json', **self.headers}

            # Send POST to webhook
            async with session.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status in (200, 201, 202, 204)

        except Exception as e:
            logger.error(f"Failed to send to webhook {self.endpoint}: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
