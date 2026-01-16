"""
JARVIS Slack Integration - Team communication via Slack.

Connects to Slack Web API for:
- Sending messages
- Reading channels
- Managing notifications
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class SlackChannel:
    """A Slack channel."""
    id: str
    name: str
    is_private: bool
    is_member: bool
    topic: str


@dataclass
class SlackMessage:
    """A Slack message."""
    ts: str  # Timestamp ID
    user: str
    text: str
    channel: str
    timestamp: datetime


class SlackClient:
    """
    Client for Slack Web API.
    
    Features:
    - Send messages
    - List channels
    - Read message history
    - User info
    """
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(self, token: str = None):
        """
        Initialize Slack client.
        
        Args:
            token: Slack Bot OAuth token (from env if not provided)
        """
        self.token = token or os.environ.get("SLACK_TOKEN")
        self._client = None
        
        if not HTTPX_AVAILABLE:
            print("Warning: httpx not installed. Run: pip install httpx")
    
    def _get_client(self):
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    def is_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return bool(self.token) and HTTPX_AVAILABLE
    
    def get_channels(self, limit: int = 20) -> List[SlackChannel]:
        """
        Get list of channels the bot can access.
        
        Args:
            limit: Maximum channels to return
            
        Returns:
            List of SlackChannel objects
        """
        if not self.is_configured():
            return []
        
        try:
            response = self._get_client().get(
                "/conversations.list",
                params={"limit": limit, "types": "public_channel,private_channel"},
            )
            data = response.json()
            
            if not data.get("ok"):
                print(f"Slack error: {data.get('error')}")
                return []
            
            channels = []
            for ch in data.get("channels", []):
                channels.append(SlackChannel(
                    id=ch.get("id", ""),
                    name=ch.get("name", ""),
                    is_private=ch.get("is_private", False),
                    is_member=ch.get("is_member", False),
                    topic=ch.get("topic", {}).get("value", ""),
                ))
            return channels
            
        except Exception as e:
            print(f"Error getting channels: {e}")
            return []
    
    def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: str = None,
    ) -> Optional[SlackMessage]:
        """
        Send a message to a channel.
        
        Args:
            channel: Channel ID or name (with #)
            text: Message text
            thread_ts: Optional thread timestamp for replies
            
        Returns:
            Sent SlackMessage or None
        """
        if not self.is_configured():
            return None
        
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        try:
            response = self._get_client().post("/chat.postMessage", json=payload)
            data = response.json()
            
            if not data.get("ok"):
                print(f"Slack error: {data.get('error')}")
                return None
            
            return SlackMessage(
                ts=data.get("ts", ""),
                user="bot",
                text=text,
                channel=channel,
                timestamp=datetime.now(),
            )
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def get_messages(
        self,
        channel: str,
        limit: int = 10,
    ) -> List[SlackMessage]:
        """
        Get recent messages from a channel.
        
        Args:
            channel: Channel ID
            limit: Number of messages
            
        Returns:
            List of SlackMessage objects
        """
        if not self.is_configured():
            return []
        
        try:
            response = self._get_client().get(
                "/conversations.history",
                params={"channel": channel, "limit": limit},
            )
            data = response.json()
            
            if not data.get("ok"):
                print(f"Slack error: {data.get('error')}")
                return []
            
            messages = []
            for msg in data.get("messages", []):
                try:
                    ts = float(msg.get("ts", 0))
                    timestamp = datetime.fromtimestamp(ts)
                except:
                    timestamp = datetime.now()
                
                messages.append(SlackMessage(
                    ts=msg.get("ts", ""),
                    user=msg.get("user", "unknown"),
                    text=msg.get("text", ""),
                    channel=channel,
                    timestamp=timestamp,
                ))
            return messages
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def find_channel(self, name: str) -> Optional[SlackChannel]:
        """Find a channel by name."""
        channels = self.get_channels(limit=100)
        name_lower = name.lower().lstrip("#")
        
        for ch in channels:
            if ch.name.lower() == name_lower:
                return ch
        return None
    
    def close(self):
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton
_slack_client: Optional[SlackClient] = None


def get_slack_client() -> SlackClient:
    """Get or create Slack client singleton."""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClient()
    return _slack_client


# Tool registrations
from tools.registry import tool, ToolResult


@tool(
    name="slack_send",
    description="Send a message to a Slack channel",
    category="integrations",
    examples=["send slack message to general hello team", "slack #random good morning"],
)
def slack_send(channel: str, message: str) -> ToolResult:
    """Send Slack message."""
    client = get_slack_client()
    
    if not client.is_configured():
        return ToolResult(
            success=False,
            error="Slack not configured. Set SLACK_TOKEN environment variable.",
        )
    
    # Find channel if name provided
    if not channel.startswith("C"):
        ch = client.find_channel(channel)
        if ch:
            channel = ch.id
        else:
            return ToolResult(success=False, error=f"Channel '{channel}' not found")
    
    result = client.send_message(channel, message)
    
    if result:
        return ToolResult(success=True, output=f"Message sent to {channel}")
    return ToolResult(success=False, error="Failed to send message")


@tool(
    name="slack_channels",
    description="List available Slack channels",
    category="integrations",
    examples=["show slack channels", "list my slack channels"],
)
def slack_channels() -> ToolResult:
    """List Slack channels."""
    client = get_slack_client()
    
    if not client.is_configured():
        return ToolResult(
            success=False,
            error="Slack not configured. Set SLACK_TOKEN environment variable.",
        )
    
    channels = client.get_channels()
    
    if not channels:
        return ToolResult(success=True, output="No channels found")
    
    output = [f"Available channels ({len(channels)}):"]
    for ch in channels:
        private = "🔒" if ch.is_private else "#"
        output.append(f"  {private}{ch.name}")
    
    return ToolResult(success=True, output="\n".join(output))


@tool(
    name="slack_read",
    description="Read recent messages from a Slack channel",
    category="integrations",
    examples=["read slack general", "show messages from #random"],
)
def slack_read(channel: str, count: int = 5) -> ToolResult:
    """Read Slack messages."""
    client = get_slack_client()
    
    if not client.is_configured():
        return ToolResult(
            success=False,
            error="Slack not configured. Set SLACK_TOKEN environment variable.",
        )
    
    # Find channel if name provided
    if not channel.startswith("C"):
        ch = client.find_channel(channel)
        if ch:
            channel = ch.id
        else:
            return ToolResult(success=False, error=f"Channel '{channel}' not found")
    
    messages = client.get_messages(channel, count)
    
    if not messages:
        return ToolResult(success=True, output="No messages found")
    
    output = [f"Recent messages ({len(messages)}):"]
    for msg in reversed(messages):  # Show oldest first
        time_str = msg.timestamp.strftime("%H:%M")
        text = msg.text[:100] + "..." if len(msg.text) > 100 else msg.text
        output.append(f"  [{time_str}] {msg.user}: {text}")
    
    return ToolResult(success=True, output="\n".join(output))


if __name__ == "__main__":
    print("Testing Slack Integration...")
    
    client = SlackClient()
    
    if client.is_configured():
        print("Slack configured!")
        channels = client.get_channels(limit=5)
        print(f"Found {len(channels)} channels")
        for ch in channels:
            print(f"  - #{ch.name}")
    else:
        print("Slack not configured. Set SLACK_TOKEN environment variable.")
    
    print("\nSlack integration test complete!")
