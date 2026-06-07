from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Generator

# ============================================================================
# Configuration
# ============================================================================

def _get_db_path() -> Path:
    """Get database path from environment or use default."""
    # Priority 1: Direct path from CREDIBLE_DB_PATH
    direct_path = os.environ.get("CREDIBLE_DB_PATH")
    if direct_path:
        return Path(direct_path)

    # Priority 2: Standard DATABASE_URL (sqlite:/// format)
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        path_str = db_url.replace("sqlite:///", "")
        return Path(path_str)
    elif db_url:
        print(f"⚠️  DATABASE_URL is set to '{db_url}' but only SQLite is supported.")
        print("   Using default SQLite path instead.")

    # Default fallback for development
    default_path = Path(__file__).resolve().parents[1] / "data" / "auth.sqlite3"
    return default_path

DB_PATH = _get_db_path()
LEGACY_JSON_PATH = Path(__file__).resolve().parents[1] / "data.json"
DEFAULT_SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 8 * 60 * 60))
DEFAULT_PASSWORD_RESET_TTL_SECONDS = 60 * 60  # 1 hour
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", 12))

# Global initialization flag
_DB_INITIALIZED = False

# ============================================================================
# SQLite Helpers
# ============================================================================

@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    Use this instead of raw _connect() for proper cleanup.
    """
    conn = None
    try:
        # Handle in-memory database for testing
        if str(DB_PATH) == ":memory:":
            conn = sqlite3.connect(":memory:")
        else:
            # Ensure directory exists for file-based DB
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(DB_PATH))
        
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency for SQLite
        conn.execute("PRAGMA busy_timeout = 5000")  # Wait 5 seconds if locked
        
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Type Definitions

@dataclass(frozen=True)
class User:
    """User record with organization memberships."""
    user_id: str
    full_name: str
    work_email: str
    password_hash: str
    created_at: str
    organizations: list[dict[str, Any]]  # Can be refined later


@dataclass(frozen=True)
class SessionRecord:
    """Active session record."""
    session_token: str
    user_id: str
    expires_at_utc: str


@dataclass(frozen=True)
class PasswordResetRecord:
    """Password reset token record."""
    token: str
    user_id: str
    expires_at_utc: str

@dataclass(frozen=True)
class Membership:
    """User's organization membership."""
    org_id: str
    name: str
    role: str
    created_at: str

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(dt: datetime | None = None) -> str:
    current = dt or _utc_now()
    return current.isoformat(timespec="seconds")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    import bcrypt
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# ============================================================================
# Database Initialization (Called ONCE at app startup)
# ============================================================================

def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    connection.executescript(
        """
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
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at_utc TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS password_resets (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at_utc TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """
    )


def _load_legacy_json_if_needed(connection: sqlite3.Connection) -> None:
    """Import data from legacy JSON file if database is empty."""
    user_count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if user_count > 0 or not LEGACY_JSON_PATH.exists():
        return

    print(f"📦 Importing legacy data from {LEGACY_JSON_PATH}")
    
    with LEGACY_JSON_PATH.open("r", encoding="utf-8") as handle:
        legacy = json.load(handle)

    for org in legacy.get("orgs", []):
        connection.execute(
            "INSERT OR IGNORE INTO organizations (org_id, name, created_at_utc) VALUES (?, ?, ?)",
            (org.get("org_id") or f"org_{token_urlsafe(6)}", org.get("name", ""), _utc_iso()),
        )

    for user in legacy.get("users", []):
        user_id = user.get("user_id") or f"user_{token_urlsafe(8)}"
        connection.execute(
            """
            INSERT OR IGNORE INTO users (user_id, full_name, work_email, password_hash, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user.get("full_name", ""),
                user.get("work_email", "").lower(),
                user.get("password_hash", ""),
                user.get("created_at") or _utc_iso(),
            ),
        )

        organization_name = user.get("organization")
        if organization_name:
            org_row = connection.execute(
                "SELECT org_id FROM organizations WHERE name = ?",
                (organization_name,),
            ).fetchone()
            if org_row is None:
                org_id = f"org_{token_urlsafe(6)}"
                connection.execute(
                    "INSERT INTO organizations (org_id, name, created_at_utc) VALUES (?, ?, ?)",
                    (org_id, organization_name, _utc_iso()),
                )
            else:
                org_id = org_row["org_id"]
            
            connection.execute(
                """
                INSERT OR IGNORE INTO memberships (user_id, org_id, role, created_at_utc)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, org_id, user.get("role", "analyst"), _utc_iso()),
            )


def init_db() -> None:
    """
    Initialize the database.
    Call this ONCE when your application starts.
    """
    global _DB_INITIALIZED
    
    if _DB_INITIALIZED:
        return
    
    with _get_connection() as connection:
        _ensure_schema(connection)
        _load_legacy_json_if_needed(connection)
    
    _DB_INITIALIZED = True
    print(f"✅ SQLite database initialized at: {DB_PATH}")


# ============================================================================
# User Operations
# ============================================================================

def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "work_email": row["work_email"],
        "password_hash": row["password_hash"],
        "created_at": row["created_at_utc"],
    }


def _get_memberships(connection: sqlite3.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
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


def get_user_by_email(email: str) -> User | None:
    """
    Retrieve a user by their work email address.

    Args:
        email: The work email address to search for.

    Returns:
        A User object if found, otherwise None.
    """
    with _get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE lower(work_email) = lower(?)",
            (email.strip(),),
        ).fetchone()
        
        if row is None:
            return None
        
        memberships = _get_memberships(connection, row["user_id"])
        
        return User(
            user_id=row["user_id"],
            full_name=row["full_name"],
            work_email=row["work_email"],
            password_hash=row["password_hash"],
            created_at=row["created_at_utc"],
            organizations=memberships,
        )


def get_user_by_id(user_id: str) -> User | None:
    """
    Retrieve a user by their unique user ID.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A User object if found, otherwise None.
    """
    with _get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        
        if row is None:
            return None
        
        memberships = _get_memberships(connection, user_id)
        
        return User(
            user_id=row["user_id"],
            full_name=row["full_name"],
            work_email=row["work_email"],
            password_hash=row["password_hash"],
            created_at=row["created_at_utc"],
            organizations=memberships,
        )


def verify_password(user: User | dict[str, Any], password: str) -> bool:
    """
    Verify if the provided password matches the stored password hash.

    Args:
        user: The user object (User dataclass or dict) containing the password_hash.
        password: The plain-text password to verify.

    Returns:
        True if the password is correct, False otherwise.
    """
    import bcrypt
    if isinstance(user, User):
        stored_hash = user.password_hash
    else:
        stored_hash = user.get("password_hash")

    if not stored_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def create_user(
    full_name: str,
    work_email: str,
    organization: str,
    password: str,
    role: str = "analyst"
) -> User:
    """
    Create a new user and their primary organization membership.

    Args:
        full_name: The user's full name.
        work_email: The user's work email address.
        organization: The name of the organization they belong to.
        password: The plain-text password to be hashed and stored.
        role: The role of the user within the organization (default: "analyst").

    Returns:
        The newly created User object.

    Raises:
        ValueError: If the user already exists or creation fails.
    """
    with _get_connection() as connection:
        # Check if user exists
        existing = connection.execute(
            "SELECT user_id FROM users WHERE lower(work_email) = lower(?)",
            (work_email.strip(),),
        ).fetchone()
        
        if existing is not None:
            raise ValueError("User already exists")

        # Create user
        user_id = f"user_{token_urlsafe(8)}"
        
        # Get or create organization
        org_row = connection.execute(
            "SELECT org_id FROM organizations WHERE lower(name) = lower(?)",
            (organization.strip(),),
        ).fetchone()
        
        if org_row is None:
            org_id = f"org_{token_urlsafe(6)}"
            connection.execute(
                "INSERT INTO organizations (org_id, name, created_at_utc) VALUES (?, ?, ?)",
                (org_id, organization.strip(), _utc_iso()),
            )
        else:
            org_id = org_row["org_id"]

        # Insert user
        connection.execute(
            """
            INSERT INTO users (user_id, full_name, work_email, password_hash, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                full_name.strip(),
                work_email.strip().lower(),
                _hash_password(password),
                _utc_iso(),
            ),
        )
        
        # Create membership
        connection.execute(
            """
            INSERT INTO memberships (user_id, org_id, role, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, org_id, role, _utc_iso()),
        )

    # Return created user
    user = get_user_by_id(user_id)
    if user is None:
        raise ValueError("Unable to create user")
    return user


# ============================================================================
# Session Operations
# ============================================================================

def _delete_expired_sessions(connection: sqlite3.Connection) -> None:
    """Delete all expired sessions."""
    now_iso = _utc_iso()
    connection.execute("DELETE FROM sessions WHERE expires_at_utc <= ?", (now_iso,))


def create_session(user_id: str, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> SessionRecord:
    """
    Create a new active session for a user.

    Args:
        user_id: The unique identifier of the user.
        ttl_seconds: Time-to-live for the session in seconds.

    Returns:
        A SessionRecord object.
    """
    session_token = token_urlsafe(32)
    expires_at = _utc_now() + timedelta(seconds=ttl_seconds)
    
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (session_token, user_id, expires_at_utc, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (session_token, user_id, _utc_iso(expires_at), _utc_iso()),
        )
    
    return SessionRecord(
        session_token=session_token,
        user_id=user_id,
        expires_at_utc=_utc_iso(expires_at),
    )


def get_session(token: str) -> SessionRecord | None:
    """
    Retrieve and validate an active session by its token.

    Args:
        token: The session token to look up.

    Returns:
        A SessionRecord if the session is valid and not expired, otherwise None.
    """
    with _get_connection() as connection:
        _delete_expired_sessions(connection)
        
        row = connection.execute(
            """
            SELECT session_token, user_id, expires_at_utc
            FROM sessions
            WHERE session_token = ?
            """,
            (token,),
        ).fetchone()
        
        if row is None:
            return None
        
        expires_at = _parse_utc(row["expires_at_utc"])
        if expires_at <= _utc_now():
            connection.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
            return None
        
        return SessionRecord(
            session_token=row["session_token"],
            user_id=row["user_id"],
            expires_at_utc=row["expires_at_utc"],
        )


def delete_session(token: str) -> None:
    """
    Invalidate a session by deleting its token.

    Args:
        token: The session token to delete.
    """
    with _get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE session_token = ?", (token,))


# ============================================================================
# Password Reset Operations
# ============================================================================

def create_password_reset(
    work_email: str,
    ttl_seconds: int = DEFAULT_PASSWORD_RESET_TTL_SECONDS
) -> str:
    """
    Generate a password reset token for a given user email.

    Args:
        work_email: The email address of the user requesting a reset.
        ttl_seconds: Time-to-live for the reset token in seconds.

    Returns:
        The generated reset token.

    Raises:
        ValueError: If no account is found for the provided email.
    """
    with _get_connection() as connection:
        user_row = connection.execute(
            "SELECT user_id FROM users WHERE lower(work_email) = lower(?)",
            (work_email.strip(),),
        ).fetchone()
        
        if user_row is None:
            raise ValueError("No account found for that email.")

        token = token_urlsafe(24)
        expires_at = _utc_now() + timedelta(seconds=ttl_seconds)
        
        connection.execute(
            """
            INSERT INTO password_resets (token, user_id, expires_at_utc, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_row["user_id"], _utc_iso(expires_at), _utc_iso()),
        )
        
        return token


def consume_password_reset(token: str, new_password: str) -> bool:
    """
    Reset a user's password using a valid reset token.

    Args:
        token: The password reset token.
        new_password: The new plain-text password to set.

    Returns:
        True if the password was successfully reset, False if the token was invalid or expired.
    """
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT token, user_id, expires_at_utc
            FROM password_resets
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
        
        # Token doesn't exist
        if row is None:
            return False
        
        # Check if expired
        if _parse_utc(row["expires_at_utc"]) <= _utc_now():
            connection.execute("DELETE FROM password_resets WHERE token = ?", (token,))
            return False
        
        # Valid token - reset password
        new_hash = _hash_password(new_password)
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (new_hash, row["user_id"]),
        )
        
        # Delete the token immediately (one-time use)
        connection.execute("DELETE FROM password_resets WHERE token = ?", (token,))
        
        # Optional: Delete all active sessions for security
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
        
        return True


def cleanup_old_password_resets(days_to_keep: int = 7) -> int:
    """
    Delete expired and old password reset tokens.
    Returns number of deleted rows.
    """
    cutoff_date = _utc_iso(_utc_now() - timedelta(days=days_to_keep))
    
    with _get_connection() as connection:
        result = connection.execute(
            """
            DELETE FROM password_resets 
            WHERE expires_at_utc <= ?
               OR created_at_utc <= ?
            """,
            (_utc_iso(), cutoff_date),
        )
        return result.rowcount


def get_password_reset_token(token: str) -> PasswordResetRecord | None:
    """Get a password reset token record (for validation)."""
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT token, user_id, expires_at_utc
            FROM password_resets
            WHERE token = ?
            """,
            (token,),
        ).fetchone()

        if row is None:
            return None

        return PasswordResetRecord(
            token=row["token"],
            user_id=row["user_id"],
            expires_at_utc=row["expires_at_utc"],
        )