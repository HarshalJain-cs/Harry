"""
JARVIS Password Vault - Secure credential storage.

Encrypted storage for passwords, API keys, and sensitive credentials.
"""

import os
import json
import secrets
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from pathlib import Path

from .encryption import EncryptionManager, SecureStorage, CRYPTO_AVAILABLE


@dataclass
class Credential:
    """A stored credential."""
    id: str
    name: str
    username: Optional[str]
    password: str  # Will be encrypted
    url: Optional[str]
    notes: Optional[str]
    category: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]


class PasswordVault:
    """
    Secure password and credential vault.
    
    Features:
    - AES-256 encrypted storage
    - Password generator
    - Category organization
    - Search and filtering
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/vault",
        master_password: Optional[str] = None,
    ):
        """
        Initialize password vault.
        
        Args:
            storage_path: Path for vault storage
            master_password: Master password to unlock vault
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library required for vault")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.master_password = master_password
        self.crypto = EncryptionManager()
        self.credentials: Dict[str, Credential] = {}
        self.unlocked = False
        
        if master_password:
            self.unlock(master_password)
    
    def _get_vault_file(self) -> Path:
        """Get vault file path."""
        return self.storage_path / "vault.enc"
    
    def _get_salt_file(self) -> Path:
        """Get salt file path."""
        return self.storage_path / "vault.salt"
    
    def is_initialized(self) -> bool:
        """Check if vault has been initialized."""
        return self._get_vault_file().exists()
    
    def initialize(self, master_password: str):
        """
        Initialize a new vault.
        
        Args:
            master_password: Master password for vault
        """
        if self.is_initialized():
            raise ValueError("Vault already initialized")
        
        self.master_password = master_password
        self.credentials = {}
        self.unlocked = True
        self._save()
    
    def unlock(self, master_password: str) -> bool:
        """
        Unlock the vault.
        
        Args:
            master_password: Master password
            
        Returns:
            True if unlocked successfully
        """
        if not self.is_initialized():
            raise ValueError("Vault not initialized")
        
        self.master_password = master_password
        
        try:
            self._load()
            self.unlocked = True
            return True
        except Exception:
            self.master_password = None
            return False
    
    def lock(self):
        """Lock the vault."""
        self.credentials.clear()
        self.master_password = None
        self.unlocked = False
    
    def _load(self):
        """Load and decrypt vault."""
        vault_file = self._get_vault_file()
        salt_file = self._get_salt_file()
        
        if not vault_file.exists():
            return
        
        with open(vault_file, 'r') as f:
            encrypted_data = f.read()
        
        with open(salt_file, 'r') as f:
            salt = f.read()
        
        from .encryption import EncryptedData
        encrypted = EncryptedData(ciphertext=encrypted_data, salt=salt)
        
        decrypted = self.crypto.decrypt(encrypted, self.master_password)
        data = json.loads(decrypted.decode('utf-8'))
        
        self.credentials = {}
        for cred_data in data.get("credentials", []):
            cred_data['created_at'] = datetime.fromisoformat(cred_data['created_at'])
            cred_data['updated_at'] = datetime.fromisoformat(cred_data['updated_at'])
            cred = Credential(**cred_data)
            self.credentials[cred.id] = cred
    
    def _save(self):
        """Encrypt and save vault."""
        if not self.master_password:
            raise ValueError("Vault locked")
        
        data = {
            "credentials": [
                {
                    **asdict(c),
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in self.credentials.values()
            ],
        }
        
        json_data = json.dumps(data)
        encrypted = self.crypto.encrypt(json_data, self.master_password)
        
        with open(self._get_vault_file(), 'w') as f:
            f.write(encrypted.ciphertext)
        
        with open(self._get_salt_file(), 'w') as f:
            f.write(encrypted.salt)
    
    def _ensure_unlocked(self):
        """Ensure vault is unlocked."""
        if not self.unlocked:
            raise ValueError("Vault is locked")
    
    def add(
        self,
        name: str,
        password: str,
        username: str = None,
        url: str = None,
        notes: str = None,
        category: str = "general",
        tags: List[str] = None,
    ) -> Credential:
        """
        Add a credential to vault.
        
        Args:
            name: Credential name
            password: Password
            username: Username
            url: Associated URL
            notes: Notes
            category: Category
            tags: Tags
            
        Returns:
            Created Credential
        """
        self._ensure_unlocked()
        
        cred = Credential(
            id=secrets.token_urlsafe(16),
            name=name,
            username=username,
            password=password,
            url=url,
            notes=notes,
            category=category,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=tags or [],
        )
        
        self.credentials[cred.id] = cred
        self._save()
        
        return cred
    
    def get(self, cred_id: str) -> Optional[Credential]:
        """Get credential by ID."""
        self._ensure_unlocked()
        return self.credentials.get(cred_id)
    
    def search(self, query: str) -> List[Credential]:
        """Search credentials by name or URL."""
        self._ensure_unlocked()
        
        query_lower = query.lower()
        results = []
        
        for cred in self.credentials.values():
            if (query_lower in cred.name.lower() or
                (cred.url and query_lower in cred.url.lower()) or
                (cred.username and query_lower in cred.username.lower())):
                results.append(cred)
        
        return results
    
    def list_by_category(self, category: str) -> List[Credential]:
        """List credentials by category."""
        self._ensure_unlocked()
        return [c for c in self.credentials.values() if c.category == category]
    
    def get_categories(self) -> List[str]:
        """Get all categories."""
        self._ensure_unlocked()
        return list(set(c.category for c in self.credentials.values()))
    
    def update(self, cred_id: str, **kwargs) -> Optional[Credential]:
        """Update a credential."""
        self._ensure_unlocked()
        
        if cred_id not in self.credentials:
            return None
        
        cred = self.credentials[cred_id]
        
        for key, value in kwargs.items():
            if hasattr(cred, key):
                setattr(cred, key, value)
        
        cred.updated_at = datetime.now()
        self._save()
        
        return cred
    
    def delete(self, cred_id: str) -> bool:
        """Delete a credential."""
        self._ensure_unlocked()
        
        if cred_id in self.credentials:
            del self.credentials[cred_id]
            self._save()
            return True
        return False
    
    def generate_password(
        self,
        length: int = 20,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        symbols: bool = True,
    ) -> str:
        """Generate a secure random password."""
        import string
        
        chars = ""
        if uppercase:
            chars += string.ascii_uppercase
        if lowercase:
            chars += string.ascii_lowercase
        if digits:
            chars += string.digits
        if symbols:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        
        if not chars:
            chars = string.ascii_letters + string.digits
        
        return ''.join(secrets.choice(chars) for _ in range(length))


from tools.registry import tool, ToolResult, RiskLevel


@tool(
    name="generate_password",
    description="Generate a secure random password",
    category="security",
    examples=["generate password", "create strong password 20 characters"],
)
def generate_password_tool(
    length: int = 16,
    include_symbols: bool = True,
) -> ToolResult:
    """Generate password."""
    try:
        vault = PasswordVault.__new__(PasswordVault)
        password = vault.generate_password(length, symbols=include_symbols)
        
        return ToolResult(
            success=True,
            output=password,
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="save_password",
    description="Save a password to the vault",
    risk_level=RiskLevel.HIGH,
    requires_confirmation=True,
    category="security",
)
def save_password(
    name: str,
    password: str,
    username: str = None,
    category: str = "general",
) -> ToolResult:
    """Save password to vault."""
    try:
        # Note: In production, master password would come from auth session
        vault = PasswordVault(master_password="jarvis_default")
        
        if not vault.is_initialized():
            vault.initialize("jarvis_default")
        
        cred = vault.add(name, password, username=username, category=category)
        
        return ToolResult(
            success=True,
            output=f"Saved: {name} ({cred.id[:8]}...)",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_password",
    description="Search for passwords in the vault",
    category="security",
)
def find_password(query: str) -> ToolResult:
    """Search vault."""
    try:
        vault = PasswordVault(master_password="jarvis_default")
        
        if not vault.is_initialized():
            return ToolResult(success=True, output=[])
        
        results = vault.search(query)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "id": c.id[:8],
                    "name": c.name,
                    "username": c.username,
                    "category": c.category,
                }
                for c in results
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Password Vault...")
    
    if not CRYPTO_AVAILABLE:
        print("cryptography not available")
    else:
        vault = PasswordVault(storage_path="./test_vault")
        
        # Initialize
        vault.initialize("master_pass_123")
        print("Vault initialized")
        
        # Add credentials
        cred1 = vault.add("Gmail", "mypassword123", username="user@gmail.com", category="email")
        cred2 = vault.add("GitHub", vault.generate_password(), username="myuser", category="dev")
        print(f"Added: {cred1.name}, {cred2.name}")
        
        # Search
        results = vault.search("gmail")
        print(f"Search 'gmail': {len(results)} results")
        
        # Lock and unlock
        vault.lock()
        print("Vault locked")
        
        success = vault.unlock("master_pass_123")
        print(f"Unlock: {success}")
        
        # Categories
        print(f"Categories: {vault.get_categories()}")
        
        # Cleanup
        import shutil
        if os.path.exists("./test_vault"):
            shutil.rmtree("./test_vault")
    
    print("\nVault test complete!")
