import logging
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("firecrow.telemetry")

class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request.state.trace_id = str(uuid.uuid4())
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Trace-Id"] = request.state.trace_id
        logger.debug("Telemetry: %s %s completed in %.4fs", request.method, request.url.path, process_time)
        return response
