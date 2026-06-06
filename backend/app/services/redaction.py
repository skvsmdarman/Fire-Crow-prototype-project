from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_KEY_PARTS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "client_secret",
    "report_url",
    "presigned_url",
}

JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
GITHUB_TOKEN_RE = re.compile(r"\bgh[oprsu]_[A-Za-z0-9_]{20,255}\b")
AWS_ACCESS_KEY_RE = re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b")
AWS_SECRET_RE = re.compile(
    r"(?i)(aws_secret_access_key\s*[:=]\s*['\"]?)[A-Za-z0-9/+=]{32,}(['\"]?)"
)
GENERIC_SECRET_RE = re.compile(
    r"(?i)\b(password|secret|api[_-]?key|client[_-]?secret|auth[_-]?token)\b"
    r"(\s*[:=]\s*['\"]?)[^'\"\s&]{8,}(['\"]?)"
)
PRESIGNED_QUERY_KEYS = {
    "x-amz-signature",
    "x-amz-credential",
    "x-amz-security-token",
    "x-amz-expires",
    "x-amz-date",
    "x-amz-algorithm",
    "x-amz-signedheaders",
    "awsaccesskeyid",
    "signature",
    "expires",
}


def truncate_text(value: str, *, max_length: int = 4096) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}...[truncated]"


def strip_query_from_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def redact_presigned_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc or not parsed.query:
        return value

    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & PRESIGNED_QUERY_KEYS:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return value


def redact_text(value: str, *, max_length: int = 4096) -> str:
    redacted = redact_presigned_url(value)
    redacted = JWT_RE.sub("[REDACTED_JWT]", redacted)
    redacted = GITHUB_TOKEN_RE.sub("[REDACTED_GITHUB_TOKEN]", redacted)
    redacted = AWS_ACCESS_KEY_RE.sub("[REDACTED_AWS_ACCESS_KEY]", redacted)
    redacted = AWS_SECRET_RE.sub(r"\1[REDACTED]\2", redacted)
    redacted = GENERIC_SECRET_RE.sub(r"\1\2[REDACTED]\3", redacted)
    return truncate_text(redacted, max_length=max_length)


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("-", "_")
    return any(part in key_lower for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any, *, key: str | None = None, max_text_length: int = 4096) -> Any:
    if key and _is_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, str):
        if key and key.lower() in {"href", "referrer", "referrer_path", "referer"}:
            value = strip_query_from_url(value)
        return redact_text(value, max_length=max_text_length)

    if isinstance(value, dict):
        return {str(k): redact_value(v, key=str(k), max_text_length=max_text_length) for k, v in value.items()}

    if isinstance(value, list):
        return [redact_value(item, max_text_length=max_text_length) for item in value]

    return value


def safe_json_dumps(value: Any, *, max_length: int = 4096) -> str:
    redacted = redact_value(value)
    serialized = json.dumps(redacted, separators=(",", ":"), ensure_ascii=True, default=str)
    return truncate_text(serialized, max_length=max_length)
