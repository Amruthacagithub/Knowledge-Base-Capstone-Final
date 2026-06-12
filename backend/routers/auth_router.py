"""
Auth router — login endpoint.
"""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr, field_validator

from backend.config import ACCESS_TOKEN_MINUTES, AUTH_MODE, LOGIN_RATE_LIMIT_PER_MINUTE
from backend.database import SessionLocal
from backend.services.auth import (
    authenticate_password,
    create_token,
    get_user_context_by_email,
    revoke_token,
)
from backend.services.rate_limit import rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class LoginResponse(BaseModel):
    token: str
    user_id: str
    email: str
    department: str
    roles: list[str]
    expires_in: int


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Invalid email or password"},
        429: {"description": "Too many login attempts"},
    },
)
def login(req: LoginRequest, request: Request):
    """Authenticate by password, or by email only in explicit demo mode."""
    client_host = request.client.host if request.client else "unknown"
    decision = rate_limiter.check(
        f"login:{client_host}",
        LOGIN_RATE_LIMIT_PER_MINUTE,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    db = SessionLocal()
    try:
        if AUTH_MODE == "demo":
            ctx = get_user_context_by_email(db, req.email)
        else:
            password = req.password.get_secret_value() if req.password else ""
            ctx = authenticate_password(db, req.email, password)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_token(ctx.user_id, db=db)
        db.commit()

        return LoginResponse(
            token=token,
            user_id=ctx.user_id,
            email=ctx.email,
            department=ctx.department,
            roles=ctx.roles,
            expires_in=ACCESS_TOKEN_MINUTES * 60,
        )
    finally:
        db.close()


@router.post(
    "/logout",
    status_code=204,
    responses={401: {"description": "Invalid or expired token"}},
)
def logout(authorization: Annotated[str, Header()]) -> Response:
    token = authorization.removeprefix("Bearer ").strip()
    if not revoke_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return Response(status_code=204)
