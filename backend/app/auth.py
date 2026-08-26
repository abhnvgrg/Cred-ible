"""Authentication for the cred-ible API.

Replaces the previous placeholder in `experience.py`, which accepted any
string containing an "@" as a valid login, never checked the password, and
issued a session token that no endpoint verified.

Three pieces:

* **Storage** - users live in SQLite. The service was stateless before, so
  this keeps the deployment footprint to a single file with no extra
  infrastructure. Every query is parameterised, and `_row_to_user` is the only
  place a row becomes a dict, so the password hash cannot reach a response by
  accident.
* **Hashing** - `hashlib.scrypt`, which is memory-hard and in the standard
  library, so there is no new dependency to keep patched. Parameters follow
  the RFC 7914 interactive-login recommendation. Comparison is constant-time.
* **Tokens** - short-lived HS256 JWTs. The signing secret comes from the
  environment and the module refuses to issue tokens without one outside
  development, so a deployment cannot silently fall back to a default secret.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

DB_PATH = Path(
    os.getenv(
        "CREDIBLE_AUTH_DB",
        str(Path(__file__).resolve().parents[1] / "data" / "users.db"),
    )
)

# RFC 7914 interactive-login parameters: ~16 MB and roughly 100 ms per hash.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64
_SALT_BYTES = 16

_ALGORITHM = "HS256"
_ISSUER = "cred-ible"
_TOKEN_TTL = timedelta(hours=int(os.getenv("CREDIBLE_TOKEN_TTL_HOURS", "8")))

VALID_ROLES = frozenset({"analyst", "admin"})
MIN_PASSWORD_LENGTH = 12

_bearer = HTTPBearer(auto_error=False)
_EPHEMERAL_SECRET: str | None = None


class AuthError(Exception):
    """Raised for caller-correctable auth problems (bad input, duplicate user)."""


def _jwt_secret() -> str:
    global _EPHEMERAL_SECRET

    secret = os.getenv("CREDIBLE_JWT_SECRET", "").strip()
    if secret:
        if len(secret) < 32:
            raise RuntimeError(
                "CREDIBLE_JWT_SECRET must be at least 32 characters. Generate one with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return secret

    # No secret configured. Allowed only for local development, and even then
    # the key is per-process so tokens never survive a restart.
    if os.getenv("CREDIBLE_ENV", "development").lower() in {"dev", "development", "test"}:
        if _EPHEMERAL_SECRET is None:
            _EPHEMERAL_SECRET = secrets.token_urlsafe(48)
        return _EPHEMERAL_SECRET

    raise RuntimeError(
        "CREDIBLE_JWT_SECRET is not set. Refusing to issue tokens signed with a "
        "default secret. Set CREDIBLE_JWT_SECRET, or set CREDIBLE_ENV=development "
        "for local use."
    )


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the users table. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                full_name     TEXT NOT NULL,
                organization  TEXT NOT NULL,
                role          TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )


def hash_password(password: str) -> str:
    """Hash a password with scrypt. Returns `scrypt$N$r$p$salt$hash` (hex)."""
    normalised = unicodedata.normalize("NFKC", password).encode("utf-8")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        normalised,
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification against a stored `hash_password` value."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        normalised = unicodedata.normalize("NFKC", password).encode("utf-8")
        computed = hashlib.scrypt(
            normalised,
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, expected)


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    """Project a row into a safe dict. Deliberately omits `password_hash`."""
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "organization": row["organization"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def create_user(
    *,
    email: str,
    password: str,
    full_name: str,
    organization: str,
    role: str = "analyst",
) -> dict[str, Any]:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise AuthError("Please provide a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if role not in VALID_ROLES:
        raise AuthError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}.")

    user_id = f"user_{secrets.token_hex(8)}"
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO users"
                " (id, email, full_name, organization, role, password_hash, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    email,
                    full_name.strip(),
                    organization.strip(),
                    role,
                    hash_password(password),
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise AuthError("An account with that email already exists.") from exc
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row)


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    """Return the user on success, None on any failure.

    Callers must not distinguish "no such user" from "wrong password" in their
    response, or the endpoint becomes an account-enumeration oracle. A dummy
    verification runs when the user is missing so both paths take comparable
    time.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ).fetchone()

    if row is None:
        verify_password(password, hash_password("dummy-password-for-timing"))
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return _row_to_user(row)


def create_access_token(user: dict[str, Any]) -> tuple[str, int]:
    """Issue a signed JWT. Returns `(token, ttl_seconds)`."""
    now = datetime.now(timezone.utc)
    expires = now + _TOKEN_TTL
    claims = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": _ISSUER,
    }
    token = jwt.encode(claims, _jwt_secret(), algorithm=_ALGORITHM)
    return token, int(_TOKEN_TTL.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a token, or raise 401.

    `algorithms` is pinned to HS256, so a token carrying `alg: none` - or an
    asymmetric algorithm whose key the attacker controls - is rejected rather
    than trusted.
    """
    try:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency: resolve the caller from a bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(credentials.credentials)
    return {
        "id": claims["sub"],
        "email": claims.get("email", ""),
        "role": claims.get("role", ""),
    }


async def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """FastAPI dependency: caller must hold the admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an administrator account.",
        )
    return user
