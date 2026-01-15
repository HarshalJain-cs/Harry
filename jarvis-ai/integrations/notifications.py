"""
JARVIS Notifications - Cross-platform notification system.

Sends desktop and mobile notifications.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class Notification:
    """A notification."""
    id: str
    title: str
    message: str
    category: str
    priority: str  # low, normal, high, urgent
    timestamp: datetime
    read: bool = False
    actions: List[Dict] = None


class NotificationManager:
    """
    Cross-platform notification system.
    
    Features:
    - Desktop notifications (Windows toast)
    - Notification history
    - Priority levels
    - Action buttons
    - Mobile push (via webhook)
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/notifications.json",
        push_webhook_url: Optional[str] = None,
    ):
        """
        Initialize notification manager.
        
        Args:
            storage_path: Path for notification history
            push_webhook_url: Webhook for mobile push
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.push_webhook = push_webhook_url
        self.notifications: List[Notification] = []
        self.max_history = 100
        
        self._load()
    
    def _load(self):
        """Load notification history."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for item in data.get("notifications", []):
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    self.notifications.append(Notification(**item))
            except Exception:
                pass
    
    def _save(self):
        """Save notification history."""
        data = {
            "notifications": [
                {
                    **asdict(n),
                    "timestamp": n.timestamp.isoformat(),
                }
                for n in self.notifications[-self.max_history:]
            ],
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def send(
        self,
        title: str,
        message: str,
        category: str = "general",
        priority: str = "normal",
        actions: List[Dict] = None,
        desktop: bool = True,
        push: bool = False,
    ) -> Notification:
        """
        Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            category: Category (general, reminder, alert, etc.)
            priority: Priority level
            actions: Action buttons
            desktop: Show desktop notification
            push: Send push notification
            
        Returns:
            Notification object
        """
        notif = Notification(
            id=f"notif_{datetime.now().timestamp()}",
            title=title,
            message=message,
            category=category,
            priority=priority,
            timestamp=datetime.now(),
            actions=actions,
        )
        
        self.notifications.append(notif)
        self._save()
        
        if desktop:
            self._show_desktop(notif)
        
        if push and self.push_webhook:
            self._send_push(notif)
        
        return notif
    
    def _show_desktop(self, notif: Notification):
        """Show desktop notification."""
        # Try plyer first (cross-platform)
        if PLYER_AVAILABLE:
            try:
                plyer_notification.notify(
                    title=notif.title,
                    message=notif.message[:256],
                    app_name="JARVIS",
                    timeout=10,
                )
                return
            except Exception:
                pass
        
        # Windows fallback using toast
        if os.name == 'nt':
            try:
                from ctypes import windll
                windll.user32.MessageBoxW(
                    0,
                    notif.message,
                    f"JARVIS - {notif.title}",
                    0x40 if notif.priority == "normal" else 0x30,
                )
            except Exception:
                pass
    
    def _send_push(self, notif: Notification):
        """Send push notification via webhook."""
        if not self.push_webhook:
            return
        
        try:
            import urllib.request
            
            data = json.dumps({
                "title": notif.title,
                "message": notif.message,
                "priority": notif.priority,
                "category": notif.category,
            }).encode()
            
            request = urllib.request.Request(
                self.push_webhook,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            urllib.request.urlopen(request, timeout=5)
        except Exception:
            pass
    
    def get_unread(self) -> List[Notification]:
        """Get unread notifications."""
        return [n for n in self.notifications if not n.read]
    
    def get_recent(self, limit: int = 20) -> List[Notification]:
        """Get recent notifications."""
        return self.notifications[-limit:]
    
    def get_by_category(self, category: str) -> List[Notification]:
        """Get notifications by category."""
        return [n for n in self.notifications if n.category == category]
    
    def mark_read(self, notif_id: str) -> bool:
        """Mark notification as read."""
        for notif in self.notifications:
            if notif.id == notif_id:
                notif.read = True
                self._save()
                return True
        return False
    
    def mark_all_read(self):
        """Mark all notifications as read."""
        for notif in self.notifications:
            notif.read = True
        self._save()
    
    def delete(self, notif_id: str) -> bool:
        """Delete a notification."""
        for i, notif in enumerate(self.notifications):
            if notif.id == notif_id:
                del self.notifications[i]
                self._save()
                return True
        return False
    
    def clear_all(self):
        """Clear all notifications."""
        self.notifications.clear()
        self._save()
    
    # Convenience methods
    def info(self, title: str, message: str):
        """Send info notification."""
        return self.send(title, message, category="info", priority="normal")
    
    def success(self, title: str, message: str):
        """Send success notification."""
        return self.send(title, message, category="success", priority="normal")
    
    def warning(self, title: str, message: str):
        """Send warning notification."""
        return self.send(title, message, category="warning", priority="high")
    
    def error(self, title: str, message: str):
        """Send error notification."""
        return self.send(title, message, category="error", priority="urgent")
    
    def reminder(self, title: str, message: str):
        """Send reminder notification."""
        return self.send(title, message, category="reminder", priority="high")


from tools.registry import tool, ToolResult


@tool(
    name="send_notification",
    description="Send a desktop notification",
    category="notifications",
    examples=["notify me when done", "send alert", "show notification"],
)
def send_notification(
    title: str,
    message: str,
    priority: str = "normal",
) -> ToolResult:
    """Send notification."""
    try:
        manager = NotificationManager()
        notif = manager.send(title, message, priority=priority)
        
        return ToolResult(
            success=True,
            output=f"Notification sent: {title}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_notifications",
    description="Get recent notifications",
    category="notifications",
)
def get_notifications(unread_only: bool = False) -> ToolResult:
    """Get notifications."""
    try:
        manager = NotificationManager()
        
        if unread_only:
            notifs = manager.get_unread()
        else:
            notifs = manager.get_recent(20)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "title": n.title,
                    "message": n.message[:50],
                    "category": n.category,
                    "read": n.read,
                    "time": n.timestamp.strftime("%H:%M"),
                }
                for n in notifs
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="clear_notifications",
    description="Clear all notifications",
    category="notifications",
)
def clear_notifications() -> ToolResult:
    """Clear notifications."""
    try:
        manager = NotificationManager()
        manager.clear_all()
        
        return ToolResult(success=True, output="Notifications cleared")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Notification Manager...")
    
    manager = NotificationManager(storage_path="./test_notifications.json")
    
    # Send notifications
    manager.info("Test", "This is a test notification")
    manager.success("Task Complete", "Your task finished successfully")
    manager.warning("Low Battery", "Battery at 20%")
    
    print(f"Total notifications: {len(manager.notifications)}")
    print(f"Unread: {len(manager.get_unread())}")
    
    # Show recent
    for notif in manager.get_recent(5):
        status = "📬" if not notif.read else "📭"
        print(f"  {status} [{notif.category}] {notif.title}")
    
    # Cleanup
    if os.path.exists("./test_notifications.json"):
        os.remove("./test_notifications.json")
    
    print("\nNotification test complete!")
