import logging
import base64
import os
from typing import Optional

logger = logging.getLogger("firecrow.crypto")

# In production, use cryptography.fernet or AES-GCM
# For now, this serves as the AES-256-GCM abstraction layer.

class CryptoManager:
    def __init__(self):
        # We would initialize AES-256-GCM key from environment here
        self.key = os.getenv("ENCRYPTION_KEY", b"mock-encryption-key-32-bytes-long!")
        
    def encrypt_finding(self, plaintext: str) -> str:
        """Encrypts sensitive finding data before database storage."""
        if not plaintext:
            return plaintext
        # Mock encryption: base64 encode and prefix
        encoded = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
        return f"ENC[{encoded}]"

    def decrypt_finding(self, ciphertext: str) -> str:
        """Decrypts sensitive finding data from database storage."""
        if not ciphertext or not ciphertext.startswith("ENC["):
            return ciphertext
        # Mock decryption
        encoded = ciphertext[4:-1]
        try:
            return base64.b64decode(encoded).decode("utf-8")
        except Exception:
            return "ERROR_DECRYPTING"

crypto_manager = CryptoManager()
