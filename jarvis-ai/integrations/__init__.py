"""
JARVIS Integrations - External service connectors.

API integrations for popular services and platforms.
"""

from .api_client import APIClient
from .webhooks import WebhookManager
from .smart_home import SmartHomeHub
from .notifications import NotificationManager
from .calendar import CalendarManager

__all__ = [
    "APIClient",
    "WebhookManager",
    "SmartHomeHub",
    "NotificationManager",
    "CalendarManager",
]
