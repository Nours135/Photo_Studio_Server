import time
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, CollectorRegistry, push_to_gateway
from fastapi import FastAPI, Request

registry = CollectorRegistry()

# Metrics 
REQUEST_COUNT = Counter(
    "fastapi_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)

REQUEST_LATENCY = Histogram(
    "fastapi_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    registry=registry,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Record metrics for every request"""

        method = request.method
        path = request.url.path

        start_time = time.time()

        response = await call_next(request)
        status_code = response.status_code

        duration = time.time() - start_time

        # record metrics
        REQUEST_COUNT.labels(method=method, path=path, status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(duration)

        # push registry to pushgateway
        push_to_gateway(
            "pushgateway:9091",
            job="fastapi_app",
            registry=registry
        )

        return response
