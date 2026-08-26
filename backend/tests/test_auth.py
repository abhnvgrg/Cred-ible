"""Authentication and model-training authorisation.

These tests pin the behaviour that was missing before: the previous
implementation accepted any email-shaped string as a valid login, never
checked the password, and left `/model/train` open to anonymous callers with a
caller-supplied filesystem path.
"""

from __future__ import annotations

import jwt
import pytest

from app.auth import authenticate, create_user, hash_password, verify_password


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------


def test_hash_is_not_reversible_and_is_salted():
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")

    assert "correct-horse-battery" not in first
    assert first.startswith("scrypt$")
    # Distinct salts, so identical passwords must not produce identical hashes.
    assert first != second
    assert verify_password("correct-horse-battery", first)
    assert verify_password("correct-horse-battery", second)


def test_wrong_password_fails_verification():
    encoded = hash_password("correct-horse-battery")
    assert not verify_password("Correct-horse-battery", encoded)
    assert not verify_password("", encoded)


@pytest.mark.parametrize("malformed", ["", "not-a-hash", "scrypt$bad", "md5$1$2$3$4$5"])
def test_malformed_hash_is_rejected_not_crashed(malformed):
    assert verify_password("anything", malformed) is False


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------


def test_registration_returns_a_real_jwt(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "New User",
            "work_email": "new.user@example.com",
            "organization": "Acme",
            "password": "a-sufficiently-long-password",
            "confirm_password": "a-sufficiently-long-password",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    claims = jwt.decode(body["session_token"], options={"verify_signature": False})
    assert claims["sub"] == body["user_id"]
    assert claims["iss"] == "cred-ible"
    assert "exp" in claims


def test_self_registration_cannot_grant_admin(client):
    """Anyone can register, so registration must never mint an admin."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Escalation Attempt",
            "work_email": "escalate@example.com",
            "organization": "Acme",
            "password": "a-sufficiently-long-password",
            "confirm_password": "a-sufficiently-long-password",
            "role": "admin",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "analyst"


def test_duplicate_email_is_rejected(client):
    payload = {
        "full_name": "Dup",
        "work_email": "dup@example.com",
        "organization": "Acme",
        "password": "a-sufficiently-long-password",
        "confirm_password": "a-sufficiently-long-password",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 400


def test_mismatched_confirmation_is_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Mismatch",
            "work_email": "mismatch@example.com",
            "organization": "Acme",
            "password": "a-sufficiently-long-password",
            "confirm_password": "a-different-long-password",
        },
    )
    assert response.status_code == 400


def test_short_password_is_rejected_before_reaching_the_store(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Short",
            "work_email": "short@example.com",
            "organization": "Acme",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------


def test_login_requires_the_correct_password(client, analyst_headers):
    good = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )
    assert good.status_code == 200

    bad = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "wrong-password-entirely"},
    )
    assert bad.status_code == 401


def test_login_does_not_leak_whether_an_account_exists(client, analyst_headers):
    """Identical responses, or the endpoint enumerates registered emails."""
    wrong_password = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "wrong-password-entirely"},
    )
    no_such_user = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "wrong-password-entirely"},
    )
    assert wrong_password.status_code == no_such_user.status_code == 401
    assert wrong_password.json()["detail"] == no_such_user.json()["detail"]


def test_email_is_matched_case_insensitively(client):
    create_user(
        email="MixedCase@Example.com",
        password="a-sufficiently-long-password",
        full_name="Mixed",
        organization="Acme",
    )
    assert authenticate("mixedcase@example.com", "a-sufficiently-long-password")


# --------------------------------------------------------------------------
# Token verification
# --------------------------------------------------------------------------


def test_unauthenticated_caller_cannot_retrain_the_model(client):
    assert client.post("/model/train").status_code in (401, 403)


def test_garbage_token_is_rejected(client):
    response = client.post(
        "/model/train", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert response.status_code == 401


def test_alg_none_forgery_is_rejected(client):
    """A token claiming admin, signed with `alg: none`, must not be honoured."""
    forged = jwt.encode(
        {"sub": "attacker", "role": "admin", "iss": "cred-ible", "exp": 9999999999},
        key="",
        algorithm="none",
    )
    response = client.post("/model/train", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    expired = jwt.encode(
        {"sub": "u", "role": "admin", "iss": "cred-ible", "exp": 1000000000},
        key="wrong-secret-but-expiry-checked-first",
        algorithm="HS256",
    )
    response = client.post("/model/train", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_analyst_token_cannot_reach_an_admin_endpoint(client, analyst_headers):
    assert client.post("/model/train", headers=analyst_headers).status_code == 403
    assert client.get("/model/datasets", headers=analyst_headers).status_code == 403


# --------------------------------------------------------------------------
# Training input is an allowlisted name, never a path
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "probe",
    [
        "/etc/passwd",
        "C:/Windows/win.ini",
        "../../../../etc/passwd",
        "../50kborr.csv",
        "....//....//etc/passwd",
    ],
)
def test_traversal_attempts_are_rejected_for_admins_too(client, admin_headers, probe):
    response = client.post(f"/model/train?dataset={probe}", headers=admin_headers)
    assert response.status_code == 400
    # The old error echoed the resolved absolute path, confirming to a caller
    # whether a given file existed on the host.
    assert "not found at" not in response.text


def test_dataset_registry_exposes_names_only(client, admin_headers):
    response = client.get("/model/datasets", headers=admin_headers)
    assert response.status_code == 200
    for name in response.json()["datasets"]:
        assert "/" not in name and "\\" not in name


# --------------------------------------------------------------------------
# Public surface is unchanged
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/health", "/model/status", "/personas"])
def test_public_endpoints_remain_public(client, path):
    assert client.get(path).status_code == 200
