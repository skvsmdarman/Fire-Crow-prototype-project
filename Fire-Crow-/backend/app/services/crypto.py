import logging
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings

logger = logging.getLogger("firecrow.crypto")

class CryptoManager:
    def __init__(self):
        # Derive a 32-byte key from settings.ENCRYPTION_KEY or settings.SECRET_KEY.
        # In production we prefer a distinct ENCRYPTION_KEY, but can fall back to
        # SECRET_KEY when operators have not split the secrets yet.
        key_source = settings.ENCRYPTION_KEY or settings.SECRET_KEY

        if not settings.DEBUG and not settings.ENCRYPTION_KEY:
            logger.warning("ENCRYPTION_KEY is not set in production; falling back to SECRET_KEY for encryption.")

        if not key_source:
            raise RuntimeError(
                "ENCRYPTION_KEY or SECRET_KEY must be set. "
                "Encryption cannot proceed without a valid key."
            )
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
            logger.exception("Failed to encrypt data: %s", str(e))
            # Do NOT fall back to base64 - this would store plaintext as if encrypted
            raise RuntimeError(f"Encryption failed: {str(e)}") from e

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypts a generic sensitive string from database storage."""
        if not ciphertext or not ciphertext.startswith("ENC["):
            return ciphertext
        
        token = ciphertext[4:-1]
        
        # Try Fernet decryption
        try:
            decrypted_bytes = self.cipher.decrypt(token.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except Exception:
            logger.error("Failed to decrypt data using Fernet. Data may be corrupted or encrypted with a different key.")
            return "ERROR_DECRYPTING"

    def encrypt_finding(self, plaintext: str) -> str:
        """Backwards-compatible alias for finding encryption."""
        return self.encrypt_secret(plaintext)

    def decrypt_finding(self, ciphertext: str) -> str:
        """Backwards-compatible alias for finding decryption."""
        return self.decrypt_secret(ciphertext)

crypto_manager = CryptoManager()
