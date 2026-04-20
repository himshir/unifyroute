"""OpenTelemetry (OTLP) sink implementation"""

import aiohttp
import json
from typing import Optional, Dict, Any
import logging

from .base import LogSink, LogEvent, SinkConfig


logger = logging.getLogger(__name__)


class OTLPSink(LogSink):
    """Sends logs to OpenTelemetry HTTP endpoint (covers Datadog, Honeycomb, etc.)"""

    def __init__(self, config: SinkConfig, endpoint: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize OTLP sink.

        Args:
            config: Sink configuration
            endpoint: OTLP HTTP endpoint URL
            headers: Optional HTTP headers (e.g., authorization)
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
        """Send event to OTLP endpoint"""
        try:
            session = await self._ensure_session()

            # Build OTLP-compatible payload
            payload = {
                'resourceLogs': [
                    {
                        'scopeLogs': [
                            {
                                'logRecords': [
                                    {
                                        'timeUnixNano': int(event.timestamp.timestamp() * 1e9),
                                        'severityNumber': self._severity_number(event.level.value),
                                        'severityText': event.level.value,
                                        'body': {
                                            'stringValue': event.message,
                                        },
                                        'attributes': {
                                            'component': event.component,
                                            'event_type': event.event_type,
                                            'request_id': event.request_id,
                                            'client_key_id': event.client_key_id,
                                            **(event.details or {}),
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # Send to OTLP endpoint
            async with session.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status in (200, 201, 202, 204)

        except Exception as e:
            logger.error(f"Failed to send to OTLP endpoint: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    @staticmethod
    def _severity_number(level: str) -> int:
        """Convert log level to OTLP severity number (1-21)"""
        severity_map = {
            'DEBUG': 5,
            'INFO': 9,
            'WARNING': 13,
            'ERROR': 17,
            'CRITICAL': 21,
        }
        return severity_map.get(level, 9)
