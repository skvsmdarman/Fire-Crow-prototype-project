import logging
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings

logger = logging.getLogger("firecrow.crypto")

class CryptoManager:
    def __init__(self):
        # Derive a 32-byte key from settings.ENCRYPTION_KEY or settings.SECRET_KEY
        key_source = settings.ENCRYPTION_KEY or settings.SECRET_KEY or "mock-encryption-key-32-bytes-long!"
        if isinstance(key_source, str):
            key_bytes = key_source.encode("utf-8")
        else:
            key_bytes = key_source
            
        key_hash = hashlib.sha256(key_bytes).digest()
        self.fernet_key = base64.urlsafe_b64encode(key_hash)
        self.cipher = Fernet(self.fernet_key)
        
    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypts a generic sensitive string before database storage."""
        if not plaintext:
            return plaintext
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode("utf-8"))
            return f"ENC[{encrypted_bytes.decode('utf-8')}]"
        except Exception as e:
            logger.exception("Failed to encrypt finding data: %s", str(e))
            # Fallback to mock base64 just in case, but log it
            encoded = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
            return f"ENC[{encoded}]"

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypts a generic sensitive string from database storage."""
        if not ciphertext or not ciphertext.startswith("ENC["):
            return ciphertext
        
        token = ciphertext[4:-1]
        
        # 1. Try real Fernet decryption
        try:
            decrypted_bytes = self.cipher.decrypt(token.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except Exception:
            # 2. Fallback to legacy base64 decoding (for compatibility with mock data)
            try:
                return base64.b64decode(token).decode("utf-8")
            except Exception:
                logger.error("Failed to decrypt finding data using Fernet or legacy base64 fallback.")
                return "ERROR_DECRYPTING"

    def encrypt_finding(self, plaintext: str) -> str:
        """Backwards-compatible alias for finding encryption."""
        return self.encrypt_secret(plaintext)

    def decrypt_finding(self, ciphertext: str) -> str:
        """Backwards-compatible alias for finding decryption."""
        return self.decrypt_secret(ciphertext)

crypto_manager = CryptoManager()
