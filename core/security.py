import time
import secrets
from typing import Optional

from cachetools import TTLCache
from fastapi import HTTPException, status, Request, Cookie
from fastapi.responses import JSONResponse

from core.config import CORS_ORIGINS

SESSION_TTL = 7 * 24 * 60 * 60  # 7 hari
SESSIONS = TTLCache(maxsize=10_000, ttl=SESSION_TTL)

def create_session() -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = True
    return token

def delete_session(session_token: Optional[str]) -> None:
    if session_token:
        SESSIONS.pop(session_token, None)

def verify_access(request: Request) -> str:
    session_token = request.cookies.get("dl_auth")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session tidak ditemukan"
        )

    if session_token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session tidak valid atau telah kedaluwarsa"
        )
    
    return session_token

def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.client.host or "127.0.0.1"

FAILED_ATTEMPTS = TTLCache(maxsize=10_000, ttl=300)
async def rate_limit_auth_middleware(request: Request, call_next):

    is_auth_endpoint = request.url.path == "/api/auth"
    
    if is_auth_endpoint:
        client_ip = get_client_ip(request)
        now = time.time()
        
        record = FAILED_ATTEMPTS.get(client_ip, {"count": 0, "blocked_until": 0})
        
        if now < record["blocked_until"]:
            remaining = int(record["blocked_until"] - now)

            origin = request.headers.get("origin")
            headers = {}

            if origin in CORS_ORIGINS:
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Terlalu banyak percobaan salah. Silakan tunggu {remaining} detik.",
                    "retry_after": remaining
                },
                headers=headers
            )

    response = await call_next(request)

    if is_auth_endpoint:
        client_ip = get_client_ip(request)
        now = time.time()
        
        if response.status_code == 401:
            record = FAILED_ATTEMPTS.get(client_ip, {"count": 0, "blocked_until": 0})
            record["count"] += 1
            
            if record["count"] >= 5:
                record["blocked_until"] = now + 60
                record["count"] = 0
            
            FAILED_ATTEMPTS[client_ip] = record

        elif response.status_code == 200:
            FAILED_ATTEMPTS.pop(client_ip, None)

    return response