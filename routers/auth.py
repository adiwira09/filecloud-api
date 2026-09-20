from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from core.config import AUTH_TOKEN
from core.security import (
    create_session,
    delete_session,
    SESSIONS,
)

router = APIRouter()

class LoginRequest(BaseModel):
    access_key: str

@router.post("/auth")
def login(data: LoginRequest, response: Response):
    if not AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_TOKEN belum dikonfigurasi",
        )

    if data.access_key != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Key tidak valid",
        )

    session_token = create_session()

    response.set_cookie(
        key="dl_auth",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    return {
        "authenticated": True,
    }

@router.get("/auth/me")
def check_session(request: Request):
    session_token = request.cookies.get("dl_auth")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session tidak ditemukan",
        )

    if session_token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session tidak valid atau sudah expired",
        )

    return {
        "authenticated": True,
    }

@router.post("/auth/logout")
def logout(request: Request, response: Response):
    session_token = request.cookies.get("dl_auth")

    delete_session(session_token)

    response.delete_cookie(
        key="dl_auth",
        path="/",
    )

    return {
        "authenticated": False,
    }
