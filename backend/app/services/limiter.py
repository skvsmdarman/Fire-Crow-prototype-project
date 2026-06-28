from slowapi import Limiter
from slowapi.extension import StrOrCallableStr
from slowapi.util import get_remote_address

from app.config import settings


default_limits: list[StrOrCallableStr] = [] if settings.DEBUG else ["100/hour"]
limiter = Limiter(key_func=get_remote_address, default_limits=default_limits)
