"""Syslog sink implementation"""

import logging
import logging.handlers
from typing import Optional
from .base import LogSink, LogEvent, SinkConfig


class SyslogSink(LogSink):
    """Sends logs to syslog (local or remote)"""

    def __init__(self, config: SinkConfig, address: tuple = ('localhost', 514)):
        """
        Initialize syslog sink.

        Args:
            config: Sink configuration
            address: (host, port) for remote syslog, or '/dev/log' for local
        """
        super().__init__(config)
        self.address = address
        self.handler: Optional[logging.handlers.SysLogHandler] = None
        self._setup()

    def _setup(self) -> None:
        """Set up syslog handler"""
        try:
            if isinstance(self.address, str):
                # Local syslog
                self.handler = logging.handlers.SysLogHandler(self.address)
            else:
                # Remote syslog
                self.handler = logging.handlers.SysLogHandler(self.address)

            # Set formatter
            formatter = logging.Formatter(
                '%(name)s[%(process)d]: [%(request_id)s] %(levelname)s: %(message)s'
            )
            self.handler.setFormatter(formatter)
        except Exception as e:
            import logging as std_logging
            std_logging.error(f"Failed to setup syslog handler: {e}")

    async def send(self, event: LogEvent) -> bool:
        """Send event to syslog"""
        if not self.handler:
            return False

        try:
            # Convert LogLevel to logging level
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
            }
            level = level_map.get(event.level.value, logging.INFO)

            # Create log record
            logger = logging.getLogger(event.component)
            logger.log(
                level,
                f"[{event.event_type}] {event.message}",
                extra={'request_id': event.request_id or 'N/A'}
            )

            return True
        except Exception as e:
            import logging as std_logging
            std_logging.error(f"Failed to send to syslog: {e}")
            return False

    def close(self) -> None:
        """Close syslog handler"""
        if self.handler:
            self.handler.close()
