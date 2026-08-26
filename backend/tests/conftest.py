"""Shared fixtures.

Environment is configured before `app` is imported: `auth` reads its database
path and secret policy at import time, so setting these afterwards would have
no effect and the suite would write to the real users database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("CREDIBLE_ENV", "test")
os.environ.setdefault(
    "CREDIBLE_AUTH_DB", str(Path(tempfile.mkdtemp(prefix="credible-test-")) / "users.db")
)

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_user  # noqa: E402
from app.main import app  # noqa: E402

ANALYST_PASSWORD = "correct-horse-battery"
ADMIN_PASSWORD = "another-long-password"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["session_token"]


@pytest.fixture
def analyst_headers(client) -> dict[str, str]:
    email = "analyst@example.com"
    try:
        create_user(
            email=email,
            password=ANALYST_PASSWORD,
            full_name="Analyst",
            organization="Acme",
            role="analyst",
        )
    except Exception:
        pass  # already created by an earlier test in the session
    return {"Authorization": f"Bearer {_token_for(client, email, ANALYST_PASSWORD)}"}


@pytest.fixture
def admin_headers(client) -> dict[str, str]:
    email = "admin@example.com"
    try:
        create_user(
            email=email,
            password=ADMIN_PASSWORD,
            full_name="Admin",
            organization="Acme",
            role="admin",
        )
    except Exception:
        pass
    return {"Authorization": f"Bearer {_token_for(client, email, ADMIN_PASSWORD)}"}
