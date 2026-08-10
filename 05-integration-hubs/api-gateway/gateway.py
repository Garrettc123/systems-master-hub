#!/usr/bin/env python3
"""
API Gateway v2 - Enterprise Ecosystem Unified API Layer
FastAPI-based gateway with OAuth2, rate limiting, and observability
"""

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import httpx
import logging
import os
import secrets
import time
from collections import OrderedDict
from typing import Optional
import jwt
from datetime import datetime, timedelta

logger = logging.getLogger("api-gateway")

app = FastAPI(
    title="Enterprise API Gateway v2",
    description="Unified API layer for $102M+ AI enterprise ecosystem",
    version="2.0.0"
)

# CORS — never combine a wildcard origin with credentials, that would let any
# site on the internet make authenticated cross-origin calls. Origins are
# supplied explicitly via ALLOWED_ORIGINS (comma separated).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=bool(ALLOWED_ORIGINS),
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Prometheus Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP Request Duration', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP Errors', ['endpoint', 'error_type'])

# Service Registry
SERVICES = {
    "autohelix": os.getenv("AUTOHELIX_URL", "http://autohelix:8000"),
    "apex": os.getenv("APEX_URL", "http://apex:8001"),
    "mlops": os.getenv("MLOPS_URL", "http://mlops:8100"),
    "nwu": os.getenv("NWU_URL", "http://nwu:8200"),
    "ai-ops": os.getenv("AIOPS_URL", "http://ai-ops:8300"),
    "tree-of-life": os.getenv("TOL_URL", "http://tree-of-life:3000"),
}

# JWT Configuration — no hardcoded fallback. In production the secret must be
# injected; otherwise an ephemeral one is generated so tokens cannot be forged
# with a well-known key.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("JWT_SECRET must be set when ENVIRONMENT=production")
    SECRET_KEY = secrets.token_urlsafe(64)
    logger.warning("JWT_SECRET not set — generated an ephemeral development secret.")

# Headers that must not be copied verbatim between hops.
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-encoding",
    "content-length", "host",
}

# Rate Limiting (simple in-memory, use Redis in production)
RATE_LIMIT_MAX_CLIENTS = int(os.getenv("RATE_LIMIT_MAX_CLIENTS", "10000"))
# OrderedDict gives us LRU semantics so the store stays bounded even when an
# attacker rotates source addresses to exhaust memory.
rate_limit_store: "OrderedDict[str, list]" = OrderedDict()

def check_rate_limit(client_ip: str, limit: int = 100, window: int = 60) -> bool:
    """Simple rate limiting - 100 requests per minute per IP"""
    now = time.time()

    # Drop clients whose window has fully expired.
    for ip in [
        ip for ip, hits in rate_limit_store.items()
        if not hits or now - hits[-1] >= window
    ]:
        del rate_limit_store[ip]

    # Hard cap: if the store is still oversized, evict least-recently-seen
    # clients so memory cannot grow without bound.
    while len(rate_limit_store) >= RATE_LIMIT_MAX_CLIENTS:
        rate_limit_store.popitem(last=False)

    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []

    # Clean old requests
    rate_limit_store[client_ip] = [req_time for req_time in rate_limit_store[client_ip] if now - req_time < window]

    if len(rate_limit_store[client_ip]) >= limit:
        rate_limit_store.move_to_end(client_ip)
        return False

    rate_limit_store[client_ip].append(now)
    rate_limit_store.move_to_end(client_ip)
    return True

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time and metrics"""
    start_time = time.time()
    
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=429).inc()
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after": 60}
        )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Gateway-Version"] = "2.0.0"
    
    # Record metrics
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(process_time)
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": len(SERVICES),
        "version": "2.0.0"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    """API Gateway root"""
    return {
        "gateway": "Enterprise API Gateway v2",
        "ecosystem_value": "$102M+",
        "services": list(SERVICES.keys()),
        "documentation": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

# Proxy routes
@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, path: str, request: Request):
    """Proxy requests to backend services"""
    if service not in SERVICES:
        ERROR_COUNT.labels(endpoint=service, error_type="service_not_found").inc()
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    target_url = f"{SERVICES[service]}/{path}"

    # Strip hop-by-hop headers so upstream framing directives cannot be
    # replayed onto a different connection (request smuggling).
    forward_headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    try:
        # follow_redirects stays disabled so a compromised backend cannot bounce
        # the gateway to an arbitrary internal host.
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                params=request.query_params,
                content=await request.body()
            )

            response_headers = {
                key: value for key, value in response.headers.items()
                if key.lower() not in HOP_BY_HOP_HEADERS
            }

            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
                headers=response_headers,
            )
    except httpx.TimeoutException:
        ERROR_COUNT.labels(endpoint=service, error_type="timeout").inc()
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except HTTPException:
        raise
    except Exception:
        # Log the cause server-side but never echo internals back to the caller.
        ERROR_COUNT.labels(endpoint=service, error_type="internal_error").inc()
        logger.exception("Proxy request to service '%s' failed", service)
        raise HTTPException(status_code=502, detail="Upstream request failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8080")),
        log_level="info",
    )
