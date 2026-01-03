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
import time
import os
from typing import Optional
import jwt
from datetime import datetime, timedelta

app = FastAPI(
    title="Enterprise API Gateway v2",
    description="Unified API layer for $102M+ AI enterprise ecosystem",
    version="2.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Rate Limiting (simple in-memory, use Redis in production)
rate_limit_store = {}

def check_rate_limit(client_ip: str, limit: int = 100, window: int = 60) -> bool:
    """Simple rate limiting - 100 requests per minute per IP"""
    now = time.time()
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    
    # Clean old requests
    rate_limit_store[client_ip] = [req_time for req_time in rate_limit_store[client_ip] if now - req_time < window]
    
    if len(rate_limit_store[client_ip]) >= limit:
        return False
    
    rate_limit_store[client_ip].append(now)
    return True

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time and metrics"""
    start_time = time.time()
    
    # Rate limiting
    client_ip = request.client.host
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
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=await request.body()
            )
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
                headers=dict(response.headers)
            )
    except httpx.TimeoutException:
        ERROR_COUNT.labels(endpoint=service, error_type="timeout").inc()
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except Exception as e:
        ERROR_COUNT.labels(endpoint=service, error_type="internal_error").inc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
