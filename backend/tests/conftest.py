from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("CREDIBLE_ENV", "test")
os.environ.setdefault(
    "CREDIBLE_DB_PATH",
    str(Path(tempfile.mkdtemp(prefix="credible-test-")) / "auth.sqlite3"),
)
os.environ.setdefault("BCRYPT_ROUNDS", "4")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_user, reset_rate_limiter  # noqa: E402
from app.main import app  # noqa: E402

ANALYST_EMAIL = "analyst@example.com"
ADMIN_EMAIL = "admin@example.com"
ANALYST_PASSWORD = "correct-horse-battery"
ADMIN_PASSWORD = "another-long-password"


@pytest.fixture(autouse=True)
def _clean_throttle():
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _ensure_user(email: str, password: str, name: str, role: str) -> None:
    try:
        create_user(
            email=email,
            password=password,
            full_name=name,
            organization="Acme",
            role=role,
        )
    except Exception:
        pass


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["session_token"]


@pytest.fixture
def analyst_token(client) -> str:
    _ensure_user(ANALYST_EMAIL, ANALYST_PASSWORD, "Analyst", "analyst")
    return _token_for(client, ANALYST_EMAIL, ANALYST_PASSWORD)


@pytest.fixture
def admin_token(client) -> str:
    _ensure_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin", "admin")
    return _token_for(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def analyst_headers(analyst_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
