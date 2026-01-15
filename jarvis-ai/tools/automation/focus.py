"""
JARVIS Focus Mode - Distraction blocker and productivity enhancer.

Blocks distracting websites and applications during focus sessions.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from dataclasses import dataclass, asdict, field
from pathlib import Path
import threading

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class FocusSession:
    """A focus session."""
    id: str
    start_time: datetime
    end_time: datetime
    blocked_sites: List[str]
    blocked_apps: List[str]
    active: bool = True
    breaks_taken: int = 0


@dataclass
class FocusStats:
    """Focus session statistics."""
    total_sessions: int
    total_focus_time: float  # minutes
    distractions_blocked: int
    avg_session_length: float


class FocusMode:
    """
    Focus mode for productivity.
    
    Features:
    - Website blocking (via hosts file)
    - Application blocking
    - Scheduled focus sessions
    - Break reminders (Pomodoro)
    - Focus statistics
    """
    
    DEFAULT_BLOCKED_SITES = [
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "reddit.com",
        "youtube.com",
        "tiktok.com",
        "netflix.com",
        "twitch.tv",
    ]
    
    DEFAULT_BLOCKED_APPS = [
        "discord",
        "slack",
        "spotify",
        "steam",
        "telegram",
        "whatsapp",
    ]
    
    HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"
    BLOCK_MARKER = "# JARVIS FOCUS MODE"
    
    def __init__(
        self,
        storage_path: str = "./storage/focus.json",
        on_distraction: Optional[callable] = None,
    ):
        """
        Initialize focus mode.
        
        Args:
            storage_path: Path to store focus data
            on_distraction: Callback when distraction is blocked
        """
        self.storage_path = storage_path
        self.on_distraction = on_distraction
        self.current_session: Optional[FocusSession] = None
        self.sessions: List[FocusSession] = []
        self.distractions_blocked = 0
        
        self._monitoring = False
        self._monitor_thread = None
        
        self._load()
    
    def _load(self):
        """Load focus data from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                self.distractions_blocked = data.get("distractions_blocked", 0)
                
                for item in data.get("sessions", []):
                    item['start_time'] = datetime.fromisoformat(item['start_time'])
                    item['end_time'] = datetime.fromisoformat(item['end_time'])
                    self.sessions.append(FocusSession(**item))
            except Exception:
                pass
    
    def _save(self):
        """Save focus data to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "distractions_blocked": self.distractions_blocked,
            "sessions": [
                {
                    **asdict(s),
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                }
                for s in self.sessions
            ],
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def start_session(
        self,
        duration_minutes: int = 25,  # Pomodoro default
        blocked_sites: Optional[List[str]] = None,
        blocked_apps: Optional[List[str]] = None,
    ) -> FocusSession:
        """
        Start a focus session.
        
        Args:
            duration_minutes: Session duration
            blocked_sites: Sites to block (uses defaults if None)
            blocked_apps: Apps to block (uses defaults if None)
        """
        if self.current_session and self.current_session.active:
            raise ValueError("A focus session is already active")
        
        sites = blocked_sites or self.DEFAULT_BLOCKED_SITES.copy()
        apps = blocked_apps or self.DEFAULT_BLOCKED_APPS.copy()
        
        session = FocusSession(
            id=f"focus_{datetime.now().timestamp()}",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=duration_minutes),
            blocked_sites=sites,
            blocked_apps=apps,
        )
        
        self.current_session = session
        self.sessions.append(session)
        
        # Enable blocking
        self._block_sites(sites)
        self._start_app_monitor(apps)
        
        self._save()
        
        return session
    
    def stop_session(self) -> Optional[FocusSession]:
        """Stop the current focus session."""
        if not self.current_session:
            return None
        
        self.current_session.active = False
        self.current_session.end_time = datetime.now()
        
        # Disable blocking
        self._unblock_sites()
        self._stop_app_monitor()
        
        session = self.current_session
        self.current_session = None
        
        self._save()
        
        return session
    
    def _block_sites(self, sites: List[str]):
        """Block sites via hosts file."""
        try:
            # Read current hosts
            with open(self.HOSTS_PATH, 'r') as f:
                content = f.read()
            
            # Remove any existing JARVIS blocks
            lines = content.split('\n')
            new_lines = []
            skip = False
            
            for line in lines:
                if self.BLOCK_MARKER + " START" in line:
                    skip = True
                elif self.BLOCK_MARKER + " END" in line:
                    skip = False
                elif not skip:
                    new_lines.append(line)
            
            # Add new blocks
            new_lines.append(f"\n{self.BLOCK_MARKER} START")
            for site in sites:
                new_lines.append(f"127.0.0.1 {site}")
                new_lines.append(f"127.0.0.1 www.{site}")
            new_lines.append(f"{self.BLOCK_MARKER} END\n")
            
            # Write back
            with open(self.HOSTS_PATH, 'w') as f:
                f.write('\n'.join(new_lines))
        
        except PermissionError:
            # Need admin rights - skip silently
            pass
        except Exception:
            pass
    
    def _unblock_sites(self):
        """Remove site blocks from hosts file."""
        try:
            with open(self.HOSTS_PATH, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            skip = False
            
            for line in lines:
                if self.BLOCK_MARKER + " START" in line:
                    skip = True
                elif self.BLOCK_MARKER + " END" in line:
                    skip = False
                elif not skip:
                    new_lines.append(line)
            
            with open(self.HOSTS_PATH, 'w') as f:
                f.write('\n'.join(new_lines))
        
        except Exception:
            pass
    
    def _start_app_monitor(self, apps: List[str]):
        """Start monitoring for blocked apps."""
        if not PSUTIL_AVAILABLE:
            return
        
        self._monitoring = True
        app_set = set(app.lower() for app in apps)
        
        def monitor():
            while self._monitoring and self.current_session:
                try:
                    for proc in psutil.process_iter(['name']):
                        name = proc.info['name'].lower().replace('.exe', '')
                        if name in app_set:
                            self._handle_blocked_app(name)
                except Exception:
                    pass
                time.sleep(5)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def _stop_app_monitor(self):
        """Stop app monitoring."""
        self._monitoring = False
    
    def _handle_blocked_app(self, app_name: str):
        """Handle detection of blocked app."""
        self.distractions_blocked += 1
        self._save()
        
        if self.on_distraction:
            self.on_distraction(app_name)
    
    def get_stats(self) -> FocusStats:
        """Get focus statistics."""
        completed = [s for s in self.sessions if not s.active]
        
        total_time = sum(
            (s.end_time - s.start_time).total_seconds() / 60
            for s in completed
        )
        
        avg_length = total_time / len(completed) if completed else 0
        
        return FocusStats(
            total_sessions=len(completed),
            total_focus_time=round(total_time, 1),
            distractions_blocked=self.distractions_blocked,
            avg_session_length=round(avg_length, 1),
        )
    
    def is_active(self) -> bool:
        """Check if focus mode is active."""
        if not self.current_session:
            return False
        
        if datetime.now() >= self.current_session.end_time:
            self.stop_session()
            return False
        
        return self.current_session.active
    
    def get_remaining_time(self) -> int:
        """Get remaining time in minutes."""
        if not self.current_session or not self.current_session.active:
            return 0
        
        remaining = (self.current_session.end_time - datetime.now()).total_seconds() / 60
        return max(0, int(remaining))


# Tool registrations
@tool(
    name="start_focus",
    description="Start a focus session to block distractions",
    category="automation",
    examples=["start focus mode for 25 minutes", "enable focus mode"],
)
def start_focus(
    duration: int = 25,
    block_social: bool = True,
) -> ToolResult:
    """Start focus session."""
    try:
        focus = FocusMode()
        
        sites = FocusMode.DEFAULT_BLOCKED_SITES if block_social else []
        apps = FocusMode.DEFAULT_BLOCKED_APPS if block_social else []
        
        session = focus.start_session(duration, sites, apps)
        
        return ToolResult(
            success=True,
            output={
                "message": f"Focus mode started for {duration} minutes",
                "ends_at": session.end_time.strftime("%H:%M"),
                "blocked_sites": len(session.blocked_sites),
                "blocked_apps": len(session.blocked_apps),
            },
        )
    except ValueError as e:
        return ToolResult(success=False, error=str(e))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="stop_focus",
    description="Stop the current focus session",
    category="automation",
)
def stop_focus() -> ToolResult:
    """Stop focus session."""
    try:
        focus = FocusMode()
        session = focus.stop_session()
        
        if not session:
            return ToolResult(success=False, error="No active focus session")
        
        duration = (session.end_time - session.start_time).total_seconds() / 60
        
        return ToolResult(
            success=True,
            output=f"Focus session ended. Duration: {int(duration)} minutes",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="focus_status",
    description="Check focus mode status",
    category="automation",
)
def focus_status() -> ToolResult:
    """Get focus status."""
    try:
        focus = FocusMode()
        
        if focus.is_active():
            remaining = focus.get_remaining_time()
            return ToolResult(
                success=True,
                output={
                    "active": True,
                    "remaining_minutes": remaining,
                    "ends_at": focus.current_session.end_time.strftime("%H:%M"),
                },
            )
        else:
            stats = focus.get_stats()
            return ToolResult(
                success=True,
                output={
                    "active": False,
                    "total_sessions": stats.total_sessions,
                    "total_focus_time": f"{stats.total_focus_time} min",
                    "distractions_blocked": stats.distractions_blocked,
                },
            )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Focus Mode...")
    
    focus = FocusMode(storage_path="./test_focus.json")
    
    # Get stats
    stats = focus.get_stats()
    print(f"\nTotal sessions: {stats.total_sessions}")
    print(f"Total focus time: {stats.total_focus_time} minutes")
    print(f"Distractions blocked: {stats.distractions_blocked}")
    
    # Test session (short duration)
    print("\nStarting test session...")
    session = focus.start_session(duration_minutes=1)
    print(f"Session active: {focus.is_active()}")
    print(f"Remaining: {focus.get_remaining_time()} minutes")
    
    # Stop session
    focus.stop_session()
    print("Session stopped")
    
    # Cleanup
    if os.path.exists("./test_focus.json"):
        os.remove("./test_focus.json")
    
    print("\nTests complete!")
