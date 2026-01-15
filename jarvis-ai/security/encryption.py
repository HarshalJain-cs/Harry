"""
JARVIS Encryption - Data encryption and secure storage.

Provides AES-256 encryption for sensitive data with key derivation.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import Optional, Union, Dict, Any
from pathlib import Path
from dataclasses import dataclass

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


@dataclass
class EncryptedData:
    """Container for encrypted data."""
    ciphertext: str  # Base64 encoded
    salt: str  # Base64 encoded
    iv: Optional[str] = None


class EncryptionManager:
    """
    Handle data encryption and decryption.
    
    Uses Fernet (AES-128-CBC with HMAC) for symmetric encryption.
    Keys derived from passwords using PBKDF2.
    """
    
    ITERATIONS = 480000  # OWASP recommendation
    
    def __init__(self):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not installed")
    
    def derive_key(self, password: str, salt: bytes = None) -> tuple:
        """
        Derive encryption key from password.
        
        Args:
            password: User password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
            backend=default_backend(),
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt(self, data: Union[str, bytes], password: str) -> EncryptedData:
        """
        Encrypt data with password.
        
        Args:
            data: Data to encrypt (string or bytes)
            password: Encryption password
            
        Returns:
            EncryptedData with ciphertext and salt
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        key, salt = self.derive_key(password)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(data)
        
        return EncryptedData(
            ciphertext=base64.b64encode(ciphertext).decode('ascii'),
            salt=base64.b64encode(salt).decode('ascii'),
        )
    
    def decrypt(self, encrypted: EncryptedData, password: str) -> bytes:
        """
        Decrypt data with password.
        
        Args:
            encrypted: EncryptedData object
            password: Decryption password
            
        Returns:
            Decrypted data as bytes
        """
        salt = base64.b64decode(encrypted.salt)
        ciphertext = base64.b64decode(encrypted.ciphertext)
        
        key, _ = self.derive_key(password, salt)
        fernet = Fernet(key)
        
        return fernet.decrypt(ciphertext)
    
    def hash_password(self, password: str, salt: bytes = None) -> tuple:
        """
        Hash a password for storage.
        
        Args:
            password: Password to hash
            salt: Optional salt
            
        Returns:
            Tuple of (hash, salt) as base64 strings
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            self.ITERATIONS,
        )
        
        return (
            base64.b64encode(hash_bytes).decode('ascii'),
            base64.b64encode(salt).decode('ascii'),
        )
    
    def verify_password(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """Verify password against stored hash."""
        salt = base64.b64decode(stored_salt)
        computed_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    def generate_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)


class SecureStorage:
    """
    Secure file storage with encryption.
    
    Features:
    - Encrypted file storage
    - JSON serialization
    - Automatic key management
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/secure",
        master_password: Optional[str] = None,
    ):
        """
        Initialize secure storage.
        
        Args:
            storage_path: Directory for encrypted files
            master_password: Master password (can set later)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.master_password = master_password
        self.crypto = EncryptionManager() if CRYPTO_AVAILABLE else None
    
    def set_master_password(self, password: str):
        """Set or change master password."""
        self.master_password = password
    
    def _ensure_password(self):
        """Ensure master password is set."""
        if not self.master_password:
            raise ValueError("Master password not set")
    
    def store(self, key: str, value: Any) -> bool:
        """
        Store encrypted value.
        
        Args:
            key: Storage key
            value: Value to store (must be JSON serializable)
            
        Returns:
            Success status
        """
        self._ensure_password()
        
        if not self.crypto:
            raise RuntimeError("Encryption not available")
        
        # Serialize value
        data = json.dumps(value)
        
        # Encrypt
        encrypted = self.crypto.encrypt(data, self.master_password)
        
        # Save to file
        filepath = self.storage_path / f"{key}.enc"
        with open(filepath, 'w') as f:
            json.dump({
                "ciphertext": encrypted.ciphertext,
                "salt": encrypted.salt,
            }, f)
        
        return True
    
    def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve and decrypt value.
        
        Args:
            key: Storage key
            
        Returns:
            Decrypted value or None
        """
        self._ensure_password()
        
        if not self.crypto:
            return None
        
        filepath = self.storage_path / f"{key}.enc"
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            encrypted = EncryptedData(
                ciphertext=data["ciphertext"],
                salt=data["salt"],
            )
            
            decrypted = self.crypto.decrypt(encrypted, self.master_password)
            return json.loads(decrypted.decode('utf-8'))
        
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        """Delete stored value."""
        filepath = self.storage_path / f"{key}.enc"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def list_keys(self) -> list:
        """List all stored keys."""
        return [f.stem for f in self.storage_path.glob("*.enc")]


if __name__ == "__main__":
    print("Testing Encryption...")
    
    if not CRYPTO_AVAILABLE:
        print("cryptography not installed")
    else:
        crypto = EncryptionManager()
        
        # Test encryption
        data = "Hello, JARVIS!"
        password = "secret123"
        
        encrypted = crypto.encrypt(data, password)
        print(f"\nOriginal: {data}")
        print(f"Encrypted: {encrypted.ciphertext[:50]}...")
        
        decrypted = crypto.decrypt(encrypted, password)
        print(f"Decrypted: {decrypted.decode()}")
        
        # Test password hashing
        hash_val, salt = crypto.hash_password("my_password")
        print(f"\nPassword hash: {hash_val[:30]}...")
        
        is_valid = crypto.verify_password("my_password", hash_val, salt)
        print(f"Verification: {is_valid}")
        
        # Test secure storage
        print("\n\nTesting Secure Storage...")
        storage = SecureStorage("./test_secure", master_password="master123")
        
        storage.store("api_key", {"service": "test", "key": "abc123"})
        print("Stored: api_key")
        
        retrieved = storage.retrieve("api_key")
        print(f"Retrieved: {retrieved}")
        
        # Cleanup
        import shutil
        if os.path.exists("./test_secure"):
            shutil.rmtree("./test_secure")
    
    print("\nEncryption test complete!")
