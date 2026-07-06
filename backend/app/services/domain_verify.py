import logging
import re
import secrets
import httpx
import dns.resolver
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.domain_verification import DomainVerification

logger = logging.getLogger("firecrow.services.domain_verify")

class DomainVerificationService:
    @staticmethod
    def get_verification_details(db: Session, domain: str, user_id: str, tenant_id: str | None = None) -> DomainVerification:
        # Check if record already exists for this user/tenant
        record = db.query(DomainVerification).filter(
            DomainVerification.domain == domain,
            DomainVerification.user_id == user_id
        ).first()

        if not record:
            token = f"firecrow-challenge-{secrets.token_hex(16)}"
            record = DomainVerification(
                user_id=user_id,
                tenant_id=tenant_id,
                domain=domain,
                verification_token=token,
                verified=False
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    async def verify_dns(domain: str, token: str) -> bool:
        txt_name = f"_firecrow-challenge.{domain}"
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5.0
            resolver.lifetime = 5.0
            answers = resolver.resolve(txt_name, "TXT")
            for rdata in answers:
                for txt_string in rdata.strings:
                    if token in txt_string.decode("utf-8"):
                        return True
        except Exception as e:
            logger.warning(f"DNS TXT resolution failed for {txt_name}: {e}")
        return False

    @staticmethod
    async def verify_html(domain: str, token: str) -> bool:
        meta_name = "firecrow-verification"
        # Try secure HTTPS first, then fallback to HTTP
        urls = [f"https://{domain}", f"http://{domain}"]
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=5.0, verify=False, follow_redirects=True) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        pattern = rf'<meta\s+[^>]*name=["\']{meta_name}["\']\s+[^>]*content=["\']{token}["\']|<meta\s+[^>]*content=["\']{token}["\']\s+[^>]*name=["\']{meta_name}["\']'
                        if re.search(pattern, response.text, re.IGNORECASE):
                            return True
            except Exception as e:
                logger.warning(f"HTML verification failed for {url}: {e}")
        return False

    @staticmethod
    async def verify_file(domain: str, token: str) -> bool:
        urls = [f"https://{domain}/.well-known/firecrow.txt", f"http://{domain}/.well-known/firecrow.txt"]
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=5.0, verify=False, follow_redirects=True) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        if token.strip() in response.text:
                            return True
            except Exception as e:
                logger.warning(f"File verification failed for {url}: {e}")
        return False
