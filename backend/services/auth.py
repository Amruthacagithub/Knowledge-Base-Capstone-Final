"""
Authentication service — JWT token creation and validation.
"""
import jwt
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import uuid

from pwdlib import PasswordHash

from backend.config import (
    ACCESS_TOKEN_MINUTES,
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_SECRET,
)
from backend.database import SessionLocal
from backend.models import AuthSession, User


_password_hash = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _password_hash.hash("not-a-real-user-password")


@dataclass
class UserContext:
    """Represents an authenticated user's context."""
    user_id: str
    email: str
    department: str
    roles: list[str]


def create_token(user_id: str, *, db=None) -> str:
    """Create a short-lived JWT and persist its revocable session identifier."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    session_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": session_id,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    owns_session = db is None
    session = db or SessionLocal()
    try:
        session.add(
            AuthSession(
                id=session_id,
                user_id=user_id,
                created_at=now,
                expires_at=expires_at,
            )
        )
        if owns_session:
            session.commit()
        else:
            session.flush()
    finally:
        if owns_session:
            session.close()
    return token


def decode_token(token: str) -> dict:
    """Decode a JWT only when all identity and lifetime claims are valid."""
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={
            "require": ["sub", "iss", "aud", "jti", "iat", "nbf", "exp"],
        },
    )


def get_user_context(user_id: str) -> UserContext | None:
    """Look up user in DB and return their context."""
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.user_id == user_id, User.is_active.is_(True))
            .first()
        )
        if not user:
            return None
        return user_context(user)
    finally:
        db.close()


def authenticate(token: str) -> UserContext | None:
    """Validate JWT and its non-revoked server-side session."""
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        auth_session = db.get(AuthSession, str(payload["jti"]))
        if (
            auth_session is None
            or auth_session.user_id != str(payload["sub"])
            or auth_session.revoked_at is not None
            or _as_utc(auth_session.expires_at) <= now
        ):
            return None
        user = (
            db.query(User)
            .filter(
                User.user_id == str(payload["sub"]),
                User.is_active.is_(True),
            )
            .first()
        )
        return user_context(user) if user is not None else None
    finally:
        db.close()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def authenticate_password(db, email: str, password: str) -> UserContext | None:
    """Verify credentials with an equivalent dummy hash path for unknown users."""
    user = (
        db.query(User)
        .filter(User.email == email.casefold(), User.is_active.is_(True))
        .first()
    )
    encoded_hash = user.password_hash if user and user.password_hash else _DUMMY_PASSWORD_HASH
    try:
        valid = _password_hash.verify(password, encoded_hash)
    except Exception:
        valid = False
    if user is None or not user.password_hash or not valid:
        return None
    return user_context(user)


def get_user_context_by_email(db, email: str) -> UserContext | None:
    user = (
        db.query(User)
        .filter(User.email == email.casefold(), User.is_active.is_(True))
        .first()
    )
    return user_context(user) if user is not None else None


def revoke_token(token: str) -> bool:
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return False
    db = SessionLocal()
    try:
        auth_session = db.get(AuthSession, str(payload["jti"]))
        if auth_session is None or auth_session.user_id != str(payload["sub"]):
            return False
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            db.commit()
        return True
    finally:
        db.close()


def user_context(user: User) -> UserContext:
    return UserContext(
        user_id=str(user.user_id),
        email=str(user.email),
        department=str(user.department),
        roles=user.role_names(),
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
