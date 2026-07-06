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


def observe_db_pool_metrics(db_engine) -> None:
    if not PROMETHEUS_AVAILABLE or DB_CONNECTION_POOL_SIZE is None or db_engine is None:
        return

    pool = getattr(db_engine, "pool", None)
    if pool is None:
        return

    try:
        pool_size = float(pool.size()) if hasattr(pool, "size") else 0.0
        checked_in = float(pool.checkedin()) if hasattr(pool, "checkedin") else 0.0
        checked_out = float(pool.checkedout()) if hasattr(pool, "checkedout") else 0.0
        overflow = float(pool.overflow()) if hasattr(pool, "overflow") else 0.0
    except Exception:
        logger.debug("Failed to observe DB pool metrics", exc_info=True)
        return

    DB_CONNECTION_POOL_SIZE.labels(state="size").set(pool_size)
    DB_CONNECTION_POOL_SIZE.labels(state="checked_in").set(checked_in)
    DB_CONNECTION_POOL_SIZE.labels(state="checked_out").set(checked_out)
    DB_CONNECTION_POOL_SIZE.labels(state="overflow").set(overflow)


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
        if PROMETHEUS_AVAILABLE and HTTP_REQUESTS_TOTAL is not None and HTTP_REQUEST_DURATION is not None:
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
