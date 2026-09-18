from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import storage
from .storage import StorageError

AuthError = StorageError

DEFAULT_ROLE = "analyst"
ADMIN_ROLES = frozenset({"admin", "owner"})

LOGIN_MAX_ATTEMPTS = int(os.environ.get("CREDIBLE_LOGIN_MAX_ATTEMPTS", "8"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("CREDIBLE_LOGIN_WINDOW_SECONDS", "300"))

_bearer = HTTPBearer(auto_error=False)
_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = threading.Lock()
_DUMMY_HASH = storage.hash_password("timing-equalisation-placeholder")

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired session.",
    headers={"WWW-Authenticate": "Bearer"},
)


def init_db() -> None:
    storage.init_db()


def _recent(bucket: list[float], now: float) -> list[float]:
    return [stamp for stamp in bucket if now - stamp < LOGIN_WINDOW_SECONDS]


def check_login_allowed(key: str) -> None:
    now = time.monotonic()
    with _attempts_lock:
        bucket = _attempts[key] = _recent(_attempts[key], now)
        if len(bucket) < LOGIN_MAX_ATTEMPTS:
            return
        retry_after = int(LOGIN_WINDOW_SECONDS - (now - bucket[0])) + 1

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many sign-in attempts. Please try again later.",
        headers={"Retry-After": str(retry_after)},
    )


def record_login_failure(key: str) -> None:
    now = time.monotonic()
    with _attempts_lock:
        _attempts[key] = _recent(_attempts[key], now) + [now]


def clear_login_failures(key: str) -> None:
    with _attempts_lock:
        _attempts.pop(key, None)


def reset_rate_limiter() -> None:
    with _attempts_lock:
        _attempts.clear()


def primary_workspace(user: storage.User | dict[str, Any]) -> tuple[str, str]:
    if isinstance(user, storage.User):
        memberships = user.organizations
    else:
        memberships = user.get("organizations")
    if not memberships:
        return "", DEFAULT_ROLE

    primary = memberships[0]
    return primary.get("name", ""), primary.get("role", DEFAULT_ROLE)


def public_user(user: storage.User) -> dict[str, Any]:
    organization, role = primary_workspace(user)
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "work_email": user.work_email,
        "organization": organization,
        "role": role,
        "created_at": user.created_at,
    }


def create_user(
    *,
    email: str,
    password: str,
    full_name: str,
    organization: str,
    role: str = DEFAULT_ROLE,
) -> dict[str, Any]:
    user = storage.create_user(
        full_name=full_name,
        work_email=email,
        organization=organization,
        password=password,
        role=role,
    )
    return public_user(user)


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    user = storage.get_user_by_email(email)
    if user is None:
        storage.verify_password({"password_hash": _DUMMY_HASH}, password)
        return None
    if not storage.verify_password(user, password):
        return None
    return public_user(user)


def create_session(user_id: str) -> tuple[str, int]:
    record = storage.create_session(user_id=user_id)
    return record.session_token, storage.DEFAULT_SESSION_TTL_SECONDS


def end_session(token: str) -> None:
    storage.delete_session(token)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials.strip():
        raise _UNAUTHENTICATED

    token = credentials.credentials.strip()
    session = storage.get_session(token)
    if session is None:
        raise _UNAUTHENTICATED

    user = storage.get_user_by_id(session.user_id)
    if user is None:
        storage.delete_session(token)
        raise _UNAUTHENTICATED

    caller = public_user(user)
    caller["session_token"] = session.session_token
    caller["expires_at_utc"] = session.expires_at_utc
    return caller


async def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an administrator account.",
        )
    return user
