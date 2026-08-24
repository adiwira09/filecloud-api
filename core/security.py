import time
import secrets
from typing import Optional
from cachetools import TTLCache
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse

from core.config import AUTH_TOKEN

FAILED_ATTEMPTS = TTLCache(maxsize=10_000, ttl=300)

def verify_access(
    header_key: Optional[str] = Security(APIKeyHeader(name="X-API-Key", auto_error=False))
):
    if not header_key or not AUTH_TOKEN or not secrets.compare_digest(header_key, AUTH_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token akses tidak valid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return header_key

def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.client.host or "127.0.0.1"

async def rate_limit_auth_middleware(request: Request, call_next):
    if request.url.path.endswith("/storage"):
        client_ip = request.client.host
        now = time.time()
        
        record = FAILED_ATTEMPTS.get(client_ip, {"count": 0, "blocked_until": 0})
        
        if now < record["blocked_until"]:
            remaining = int(record["blocked_until"] - now)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Terlalu banyak percobaan salah. Silakan tunggu {remaining} detik.",
                    "retry_after": remaining
                }
            )

    response = await call_next(request)

    if request.url.path.endswith("/storage"):
        client_ip = request.client.host
        now = time.time()
        is_check_only = request.headers.get("X-Check-Only") == "true"
        
        if response.status_code == 401 and not is_check_only:
            record = FAILED_ATTEMPTS.get(client_ip, {"count": 0, "blocked_until": 0})
            record["count"] += 1
            
            if record["count"] >= 5:
                record["blocked_until"] = now + 60
                record["count"] = 0
            
            FAILED_ATTEMPTS[client_ip] = record
        elif response.status_code == 200:
            FAILED_ATTEMPTS.pop(client_ip, None)

    return response