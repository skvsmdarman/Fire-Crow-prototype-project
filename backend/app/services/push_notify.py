import os
import json
import logging
import base64
from pywebpush import webpush, WebPushException
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("firecrow.services.push")

KEYS_FILE = os.path.join(os.path.dirname(__file__), ".vapid_keys.json")

def load_or_generate_vapid_keys() -> tuple[str, str]:
    """Returns (private_key_pem, public_key_base64url)"""
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r") as f:
                data = json.load(f)
                return data["private_key_pem"], data["public_key_b64url"]
        except Exception:
            logger.exception("Failed to read VAPID keys file.")

    try:
        v = Vapid()
        v.generate_keys()
        private_pem = v.private_pem().decode("utf-8")
        if v.public_key is None:
            raise RuntimeError("VAPID public key was not generated.")
        
        # Get raw uncompressed public key bytes
        raw_pub = v.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        public_b64url = base64.urlsafe_b64encode(raw_pub).decode("utf-8").rstrip("=")
        
        with open(KEYS_FILE, "w") as f:
            json.dump({
                "private_key_pem": private_pem,
                "public_key_b64url": public_b64url
            }, f)
            
        logger.info("Generated new VAPID keypair and persisted to %s", KEYS_FILE)
        return private_pem, public_b64url
    except Exception as e:
        logger.exception("Failed to generate VAPID keys.")
        return "", ""

def send_web_push(subscription_info: dict, message: str) -> bool:
    private_key_pem, _ = load_or_generate_vapid_keys()
    if not private_key_pem:
        logger.error("No VAPID private key available.")
        return False
        
    try:
        webpush(
            subscription_info=subscription_info,
            data=message,
            vapid_private_key=private_key_pem,
            vapid_claims={"sub": "mailto:admin@firecrow.io"}
        )
        return True
    except WebPushException as ex:
        logger.info("Web push failed: %r", ex)
        return False
    except Exception:
        logger.exception("Unexpected error in send_web_push")
        return False
