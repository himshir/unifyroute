"""Enterprise log sinks for external backends (Phase 4)

Pluggable log sinks that send events to external systems:
- Syslog
- OpenTelemetry (OTLP) - covers Datadog, Honeycomb, Grafana, etc.
- Loki
- Webhook (generic HTTP POST)

Implemented as fire-and-forget async tasks via bounded queue.
"""

from .base import LogSink, LogEvent, SinkConfig
from .syslog_sink import SyslogSink
from .otlp_sink import OTLPSink
from .loki_sink import LokiSink
from .webhook_sink import WebhookSink
from .manager import LogSinkManager

__all__ = [
    'LogSink',
    'LogEvent',
    'SinkConfig',
    'SyslogSink',
    'OTLPSink',
    'LokiSink',
    'WebhookSink',
    'LogSinkManager',
]
