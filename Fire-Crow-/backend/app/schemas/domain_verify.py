from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
import re

class DomainVerifyRequest(BaseModel):
    domain: str = Field(..., description="The domain name to request verification for.")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        domain = v.strip().lower()
        # Clean protocol or path if user input is dirty
        if "://" in domain:
            domain = domain.split("://")[1]
        domain = domain.split("/")[0]
        # Regex to validate standard domain name format
        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*\.[a-z]{2,24}$", domain):
            raise ValueError("Invalid domain name format.")
        return domain

class DomainVerifyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str
    verification_token: str
    verified: bool
    verified_at: Optional[str] = None
    created_at: str
    dns_txt_name: str
    dns_txt_value: str
    html_meta_name: str
    html_meta_content: str
    well_known_path: str
    well_known_content: str

class DomainCheckRequest(BaseModel):
    domain: str = Field(..., description="The domain to check.")
    method: str = Field("dns", description="Verification method: 'dns', 'html', or 'file'.")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        method = v.strip().lower()
        if method not in {"dns", "html", "file"}:
            raise ValueError("Method must be one of: 'dns', 'html', 'file'.")
        return method

class DomainCheckResponse(BaseModel):
    verified: bool
    message: str
