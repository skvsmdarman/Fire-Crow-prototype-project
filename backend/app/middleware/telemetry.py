import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

logger = logging.getLogger("firecrow.telemetry")

class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Mock OpenTelemetry tracing middleware.
        In production, this would emit OTLP spans to a collector like Jaeger or Datadog.
        """
        start_time = time.time()
        
        # Add tracing ID to request state
        request.state.trace_id = "mock-trace-id-1234"
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Trace-Id"] = request.state.trace_id
        
        # logger.debug(f"Telemetry: {request.method} {request.url.path} completed in {process_time:.4f}s")
        return response
