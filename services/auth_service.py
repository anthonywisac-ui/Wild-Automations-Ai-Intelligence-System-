"""
Auth Service — user registration, login, JWT token management.
Documented in: docs/BACKEND ARCHITECTURE.md § 2.2

Uses bcrypt for password hashing and PyJWT for tokens.
Falls back gracefully if bcrypt/jwt not installed (stubs logged).

Usage:
    from services.auth_service import AuthService
    auth = AuthService(db=database_layer)
    user = await auth.register(email, password, phone)
    tokens = await auth.login(email, password)
    user_id = await auth.validate_token(access_token)
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = int(os.getenv("JWT_EXPIRE_HOURS", "24"))


def _hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        logger.warning("auth_service: bcrypt not installed, using sha256 (dev only)")
        return hashlib.sha256((password + JWT_SECRET).encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ImportError:
        import hashlib
        return hashlib.sha256((password + JWT_SECRET).encode()).hexdigest() == hashed


def _create_token(user_id: str, expires_hours: int = ACCESS_TOKEN_EXPIRE) -> str:
    try:
        import jwt
        payload = {
            "sub": user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except ImportError:
        logger.warning("auth_service: PyJWT not installed, returning opaque token")
        return secrets.token_urlsafe(32)


def _decode_token(token: str) -> Optional[str]:
    try:
        import jwt
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception as exc:
        logger.debug("auth_service: token decode failed: %s", exc)
        return None


class AuthService:
    def __init__(self, db=None) -> None:
        self._db = db

    async def register(self, email: str, password: str, phone: str) -> Dict[str, Any]:
        if not email or "@" not in email:
            raise ValueError("Invalid email")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        if self._db:
            existing = await self._safe_db_call("get_user_by_email", email)
            if existing:
                raise ValueError("User already exists")

        hashed = _hash_password(password)
        user_data = {
            "email": email,
            "password_hash": hashed,
            "phone": phone,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
        }

        if self._db:
            user_data = await self._safe_db_call("create_user", user_data) or user_data

        logger.info("auth_service: registered email=%s", email)
        return {k: v for k, v in user_data.items() if k != "password_hash"}

    async def login(self, email: str, password: str) -> Dict[str, str]:
        if not self._db:
            logger.warning("auth_service: no db — returning stub tokens")
            return {"access_token": _create_token(email), "refresh_token": _create_token(email, 168), "expires_in": str(ACCESS_TOKEN_EXPIRE * 3600)}

        user = await self._safe_db_call("get_user_by_email", email)
        if not user:
            raise ValueError("Invalid credentials")
        if not _verify_password(password, user.get("password_hash", "")):
            raise ValueError("Invalid credentials")

        user_id = str(user.get("id", email))
        access = _create_token(user_id)
        refresh = _create_token(user_id, 168)  # 7 days
        logger.info("auth_service: login user_id=%s", user_id)
        return {"access_token": access, "refresh_token": refresh, "expires_in": str(ACCESS_TOKEN_EXPIRE * 3600)}

    async def validate_token(self, token: str) -> Optional[str]:
        return _decode_token(token)

    async def _safe_db_call(self, method: str, *args) -> Any:
        if not self._db:
            return None
        fn = getattr(self._db, method, None)
        if not fn:
            logger.debug("auth_service: db has no method %s", method)
            return None
        try:
            return await fn(*args)
        except Exception as exc:
            logger.error("auth_service: db.%s error: %s", method, exc)
            return None
