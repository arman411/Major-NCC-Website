"""
crypto_utils.py — Field-level encryption for sensitive cadet data.
Uses Fernet symmetric encryption from the cryptography library.
Key is loaded from ENCRYPTION_KEY environment variable, falls back to a derived key from SECRET_KEY.
"""
import os
import base64
import hashlib

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography library not installed. Field encryption disabled.")


def _get_key():
    """Derive a valid 32-byte Fernet key from the environment."""
    raw_key = os.environ.get('ENCRYPTION_KEY')
    if raw_key:
        try:
            # If it's already a valid Fernet key (base64 encoded, 32 bytes)
            key_bytes = base64.urlsafe_b64decode(raw_key)
            if len(key_bytes) == 32:
                return base64.urlsafe_b64encode(key_bytes)
        except Exception:
            pass
    # Derive key from SECRET_KEY
    secret = os.environ.get('SECRET_KEY', 'ncc-gph-hamirpur-secret-key-2025')
    derived = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(derived)


class FieldEncryptor:
    """Encrypt/decrypt individual field values for sensitive data storage."""
    
    def __init__(self):
        if CRYPTO_AVAILABLE:
            self._fernet = Fernet(_get_key())
        else:
            self._fernet = None
    
    def encrypt(self, value: str) -> str:
        """Encrypt a string value. Returns original value if encryption unavailable."""
        if not value or not self._fernet:
            return value or ''
        try:
            return self._fernet.encrypt(value.encode()).decode()
        except Exception:
            return value
    
    def decrypt(self, value: str) -> str:
        """Decrypt an encrypted string. Returns original value if decryption fails."""
        if not value or not self._fernet:
            return value or ''
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except Exception:
            # Value may not be encrypted (legacy data)
            return value
    
    def is_available(self) -> bool:
        return self._fernet is not None


# Singleton instance
encryptor = FieldEncryptor()
