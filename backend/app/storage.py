from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Generator

import bcrypt

DEFAULT_SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 8 * 60 * 60))
PASSWORD_RESET_TTL_SECONDS = 60 * 60
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", 12))
MIN_PASSWORD_LENGTH = 12
VALID_ROLES = frozenset({"owner", "admin", "analyst"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    work_email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'analyst')),
    created_at_utc TEXT NOT NULL,
    PRIMARY KEY (user_id, org_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
"""

_initialised = False


class StorageError(ValueError):
    pass


@dataclass(frozen=True)
class User:
    user_id: str
    full_name: str
    work_email: str
    password_hash: str
    created_at: str
    organizations: list[dict[str, Any]]


@dataclass(frozen=True)
class SessionRecord:
    session_token: str
    user_id: str
    expires_at_utc: str


def _db_path() -> Path:
    direct = os.environ.get("CREDIBLE_DB_PATH")
    if direct:
        return Path(direct)

    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///"):])

    return Path(__file__).resolve().parents[1] / "data" / "auth.sqlite3"


@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
    path = _db_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    global _initialised
    if _initialised:
        return

    with _get_connection() as conn:
        conn.executescript(SCHEMA)
    _initialised = True


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(moment: datetime | None = None) -> str:
    return (moment or _utc_now()).isoformat(timespec="seconds")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _bcrypt_input(password: str) -> bytes:
    normalised = unicodedata.normalize("NFKC", password).encode("utf-8")
    return base64.b64encode(hashlib.sha256(normalised).digest())


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_bcrypt_input(password), salt).decode("utf-8")


def verify_password(user: User | dict[str, Any], password: str) -> bool:
    if isinstance(user, User):
        stored = user.password_hash
    else:
        stored = user.get("password_hash")
    if not stored:
        return False

    try:
        return bcrypt.checkpw(_bcrypt_input(password), stored.encode("utf-8"))
    except ValueError:
        return False


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise StorageError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def _memberships(conn: sqlite3.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT m.role, m.created_at_utc, o.org_id, o.name
        FROM memberships m
        JOIN organizations o ON o.org_id = m.org_id
        WHERE m.user_id = ?
        ORDER BY m.created_at_utc ASC
        """,
        (user_id,),
    ).fetchall()

    return [
        {
            "org_id": row["org_id"],
            "name": row["name"],
            "role": row["role"],
            "created_at": row["created_at_utc"],
        }
        for row in rows
    ]


def _to_user(conn: sqlite3.Connection, row: sqlite3.Row) -> User:
    return User(
        user_id=row["user_id"],
        full_name=row["full_name"],
        work_email=row["work_email"],
        password_hash=row["password_hash"],
        created_at=row["created_at_utc"],
        organizations=_memberships(conn, row["user_id"]),
    )


def get_user_by_email(email: str) -> User | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(work_email) = lower(?)",
            (email.strip(),),
        ).fetchone()
        return None if row is None else _to_user(conn, row)


def get_user_by_id(user_id: str) -> User | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return None if row is None else _to_user(conn, row)


def _org_id(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT org_id FROM organizations WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if row is not None:
        return row["org_id"]

    org_id = f"org_{token_urlsafe(6)}"
    conn.execute(
        "INSERT INTO organizations (org_id, name, created_at_utc) VALUES (?, ?, ?)",
        (org_id, name, _utc_iso()),
    )
    return org_id


def create_user(
    full_name: str,
    work_email: str,
    organization: str,
    password: str,
    role: str = "analyst",
) -> User:
    if role not in VALID_ROLES:
        raise StorageError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}.")

    email = work_email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise StorageError("Please provide a valid email address.")
    validate_password(password)

    with _get_connection() as conn:
        taken = conn.execute(
            "SELECT user_id FROM users WHERE lower(work_email) = lower(?)", (email,)
        ).fetchone()
        if taken is not None:
            raise StorageError("An account with that email already exists.")

        user_id = f"user_{token_urlsafe(8)}"
        org_id = _org_id(conn, organization.strip())

        conn.execute(
            """
            INSERT INTO users (user_id, full_name, work_email, password_hash, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, full_name.strip(), email, hash_password(password), _utc_iso()),
        )
        conn.execute(
            """
            INSERT INTO memberships (user_id, org_id, role, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, org_id, role, _utc_iso()),
        )

    created = get_user_by_id(user_id)
    if created is None:
        raise StorageError("Unable to create user.")
    return created


def create_session(user_id: str, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> SessionRecord:
    token = token_urlsafe(32)
    expires_at = _utc_iso(_utc_now() + timedelta(seconds=ttl_seconds))

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at_utc, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (_token_fingerprint(token), user_id, expires_at, _utc_iso()),
        )

    return SessionRecord(session_token=token, user_id=user_id, expires_at_utc=expires_at)


def get_session(token: str) -> SessionRecord | None:
    if not token:
        return None

    fingerprint = _token_fingerprint(token)
    with _get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at_utc <= ?", (_utc_iso(),))
        row = conn.execute(
            "SELECT user_id, expires_at_utc FROM sessions WHERE token_hash = ?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            return None

        if _parse_utc(row["expires_at_utc"]) <= _utc_now():
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (fingerprint,))
            return None

        return SessionRecord(
            session_token=token,
            user_id=row["user_id"],
            expires_at_utc=row["expires_at_utc"],
        )


def delete_session(token: str) -> None:
    if not token:
        return
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (_token_fingerprint(token),)
        )


def create_password_reset(
    work_email: str, ttl_seconds: int = PASSWORD_RESET_TTL_SECONDS
) -> str:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM users WHERE lower(work_email) = lower(?)",
            (work_email.strip(),),
        ).fetchone()
        if row is None:
            raise StorageError("No account found for that email.")

        token = token_urlsafe(32)
        conn.execute("DELETE FROM password_resets WHERE user_id = ?", (row["user_id"],))
        conn.execute(
            """
            INSERT INTO password_resets (token_hash, user_id, expires_at_utc, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (
                _token_fingerprint(token),
                row["user_id"],
                _utc_iso(_utc_now() + timedelta(seconds=ttl_seconds)),
                _utc_iso(),
            ),
        )
        return token


def consume_password_reset(token: str, new_password: str) -> bool:
    if not token:
        return False
    validate_password(new_password)

    fingerprint = _token_fingerprint(token)
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at_utc FROM password_resets WHERE token_hash = ?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            return False

        conn.execute("DELETE FROM password_resets WHERE token_hash = ?", (fingerprint,))
        if _parse_utc(row["expires_at_utc"]) <= _utc_now():
            return False

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(new_password), row["user_id"]),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
        return True
