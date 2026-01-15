"""
JARVIS Authentication - User authentication and session management.

Provides local user authentication with PIN/password support.
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class UserSession:
    """An active user session."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    device: Optional[str] = None


@dataclass
class UserProfile:
    """User profile data."""
    user_id: str
    username: str
    password_hash: str
    password_salt: str
    created_at: datetime
    last_login: Optional[datetime] = None
    settings: Dict = None
    pin_hash: Optional[str] = None
    pin_salt: Optional[str] = None


class AuthManager:
    """
    Handle user authentication.
    
    Features:
    - User registration/login
    - PIN authentication
    - Session management
    - Auto-lock timeout
    """
    
    SESSION_DURATION = timedelta(hours=8)
    LOCK_TIMEOUT = timedelta(minutes=15)
    
    def __init__(
        self,
        storage_path: str = "./storage/auth",
    ):
        """
        Initialize auth manager.
        
        Args:
            storage_path: Path for auth data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.users: Dict[str, UserProfile] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.current_session: Optional[UserSession] = None
        
        self._load()
    
    def _load(self):
        """Load auth data."""
        users_file = self.storage_path / "users.json"
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    data = json.load(f)
                
                for user_data in data:
                    user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
                    if user_data.get('last_login'):
                        user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])
                    user = UserProfile(**user_data)
                    self.users[user.user_id] = user
            except Exception:
                pass
    
    def _save(self):
        """Save auth data."""
        users_file = self.storage_path / "users.json"
        
        data = []
        for user in self.users.values():
            user_dict = asdict(user)
            user_dict['created_at'] = user.created_at.isoformat()
            if user.last_login:
                user_dict['last_login'] = user.last_login.isoformat()
            data.append(user_dict)
        
        with open(users_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _hash_password(self, password: str, salt: bytes = None) -> tuple:
        """Hash password with PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            480000,
        )
        
        return (
            hash_bytes.hex(),
            salt.hex(),
        )
    
    def _verify_hash(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """Verify password against hash."""
        salt = bytes.fromhex(stored_salt)
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    def register(self, username: str, password: str) -> UserProfile:
        """
        Register a new user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Created UserProfile
        """
        # Check if username exists
        for user in self.users.values():
            if user.username.lower() == username.lower():
                raise ValueError("Username already exists")
        
        # Create user
        user_id = secrets.token_urlsafe(16)
        password_hash, password_salt = self._hash_password(password)
        
        user = UserProfile(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            password_salt=password_salt,
            created_at=datetime.now(),
            settings={},
        )
        
        self.users[user_id] = user
        self._save()
        
        return user
    
    def login(self, username: str, password: str) -> Optional[UserSession]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            UserSession if successful, None otherwise
        """
        # Find user
        user = None
        for u in self.users.values():
            if u.username.lower() == username.lower():
                user = u
                break
        
        if not user:
            return None
        
        # Verify password
        if not self._verify_hash(password, user.password_hash, user.password_salt):
            return None
        
        # Create session
        session = UserSession(
            session_id=secrets.token_urlsafe(32),
            user_id=user.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.SESSION_DURATION,
            last_activity=datetime.now(),
        )
        
        self.sessions[session.session_id] = session
        self.current_session = session
        
        # Update last login
        user.last_login = datetime.now()
        self._save()
        
        return session
    
    def logout(self, session_id: str = None) -> bool:
        """End a session."""
        if session_id is None and self.current_session:
            session_id = self.current_session.session_id
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session = None
            return True
        return False
    
    def validate_session(self, session_id: str = None) -> bool:
        """Check if session is valid."""
        if session_id is None and self.current_session:
            session_id = self.current_session.session_id
        
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Check expiry
        if datetime.now() > session.expires_at:
            del self.sessions[session_id]
            return False
        
        # Update last activity
        session.last_activity = datetime.now()
        return True
    
    def set_pin(self, user_id: str, pin: str) -> bool:
        """Set PIN for quick unlock."""
        if user_id not in self.users:
            return False
        
        if len(pin) < 4 or len(pin) > 8:
            raise ValueError("PIN must be 4-8 digits")
        
        pin_hash, pin_salt = self._hash_password(pin)
        
        user = self.users[user_id]
        user.pin_hash = pin_hash
        user.pin_salt = pin_salt
        self._save()
        
        return True
    
    def verify_pin(self, user_id: str, pin: str) -> bool:
        """Verify PIN for quick unlock."""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        if not user.pin_hash or not user.pin_salt:
            return False
        
        return self._verify_hash(pin, user.pin_hash, user.pin_salt)
    
    def is_locked(self) -> bool:
        """Check if session is locked due to inactivity."""
        if not self.current_session:
            return True
        
        inactive_time = datetime.now() - self.current_session.last_activity
        return inactive_time > self.LOCK_TIMEOUT
    
    def get_current_user(self) -> Optional[UserProfile]:
        """Get current logged in user."""
        if not self.current_session:
            return None
        
        return self.users.get(self.current_session.user_id)
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        # Verify old password
        if not self._verify_hash(old_password, user.password_hash, user.password_salt):
            return False
        
        # Set new password
        user.password_hash, user.password_salt = self._hash_password(new_password)
        self._save()
        
        return True


from tools.registry import tool, ToolResult, RiskLevel


@tool(
    name="login",
    description="Login to JARVIS",
    category="security",
)
def login(username: str, password: str) -> ToolResult:
    """Login."""
    try:
        auth = AuthManager()
        session = auth.login(username, password)
        
        if session:
            return ToolResult(
                success=True,
                output=f"Logged in as {username}",
            )
        else:
            return ToolResult(success=False, error="Invalid credentials")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="logout",
    description="Logout from JARVIS",
    category="security",
)
def logout() -> ToolResult:
    """Logout."""
    try:
        auth = AuthManager()
        auth.logout()
        return ToolResult(success=True, output="Logged out")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="who_am_i",
    description="Get current logged in user",
    category="security",
)
def who_am_i() -> ToolResult:
    """Get current user."""
    try:
        auth = AuthManager()
        user = auth.get_current_user()
        
        if user:
            return ToolResult(
                success=True,
                output={
                    "username": user.username,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                },
            )
        else:
            return ToolResult(success=True, output="Not logged in")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Authentication...")
    
    auth = AuthManager(storage_path="./test_auth")
    
    # Register
    user = auth.register("testuser", "password123")
    print(f"Registered: {user.username}")
    
    # Login
    session = auth.login("testuser", "password123")
    print(f"Session: {session.session_id[:20]}...")
    
    # Validate
    is_valid = auth.validate_session()
    print(f"Valid session: {is_valid}")
    
    # Set PIN
    auth.set_pin(user.user_id, "1234")
    print("PIN set")
    
    # Verify PIN
    pin_valid = auth.verify_pin(user.user_id, "1234")
    print(f"PIN valid: {pin_valid}")
    
    # Logout
    auth.logout()
    print("Logged out")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_auth"):
        shutil.rmtree("./test_auth")
    
    print("\nAuth test complete!")
