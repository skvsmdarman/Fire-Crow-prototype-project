import logging
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("firecrow.telemetry")

# Try to import Prometheus client
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True

    # Define Prometheus metrics
    HTTP_REQUESTS_TOTAL = Counter(
        'firecrow_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code']
    )

    HTTP_REQUEST_DURATION = Histogram(
        'firecrow_http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )

    ACTIVE_JOBS = Gauge(
        'firecrow_active_audit_jobs',
        'Number of active audit jobs',
        ['status']
    )

    AUDIT_JOBS_TOTAL = Counter(
        'firecrow_audit_jobs_total',
        'Total audit jobs processed',
        ['status']
    )

    DB_CONNECTION_POOL_SIZE = Gauge(
        'firecrow_db_connection_pool_size',
        'Database connection pool size',
        ['state']
    )

    REDIS_CONNECTED = Gauge(
        'firecrow_redis_connected',
        'Redis connection status (1=connected, 0=disconnected)'
    )

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available. Metrics collection disabled.")
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION = None
    ACTIVE_JOBS = None
    AUDIT_JOBS_TOTAL = None
    DB_CONNECTION_POOL_SIZE = None
    REDIS_CONNECTED = None


class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request.state.trace_id = str(uuid.uuid4())

        # Extract endpoint for metrics (without query params)
        endpoint = request.url.path
        method = request.method

        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code

        # Record Prometheus metrics if available
        if PROMETHEUS_AVAILABLE:
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(process_time)

        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Trace-Id"] = request.state.trace_id
        logger.debug("Telemetry: %s %s completed in %.4fs", method, endpoint, process_time)
        return response
