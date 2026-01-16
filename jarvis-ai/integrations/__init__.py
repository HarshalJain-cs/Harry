"""
JARVIS Integrations - External service connectors.

API integrations for popular services and platforms.
"""

from .api_client import APIClient
from .webhooks import WebhookManager
from .smart_home import SmartHomeHub
from .notifications import NotificationManager
from .calendar import CalendarManager
from .wakey import WakeyClient, get_wakey_client
from .notion import NotionClient, get_notion_client
from .slack import SlackClient, get_slack_client

__all__ = [
    "APIClient",
    "WebhookManager",
    "SmartHomeHub",
    "NotificationManager",
    "CalendarManager",
    "WakeyClient",
    "get_wakey_client",
    "NotionClient",
    "get_notion_client",
    "SlackClient",
    "get_slack_client",
]
