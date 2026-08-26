from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest

from app import storage
from app.auth import authenticate, create_user
from app.storage import StorageError, _token_fingerprint, hash_password, verify_password

LONG_PASSWORD = "a-sufficiently-long-password"


def _register(client, email, name="Test User", password=LONG_PASSWORD):
    return client.post(
        "/auth/register",
        json={
            "full_name": name,
            "work_email": email,
            "organization": "Acme",
            "password": password,
            "confirm_password": password,
        },
    )


def _make_user(email, password=LONG_PASSWORD, name="Test User"):
    create_user(email=email, password=password, full_name=name, organization="Acme")
    return storage.get_user_by_email(email)


def test_hash_is_not_reversible_and_is_salted():
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")

    assert "correct-horse-battery" not in first
    assert first.startswith("$2")
    assert first != second
    assert verify_password({"password_hash": first}, "correct-horse-battery")
    assert verify_password({"password_hash": second}, "correct-horse-battery")


def test_wrong_password_fails_verification():
    encoded = hash_password("correct-horse-battery")
    assert not verify_password({"password_hash": encoded}, "Correct-horse-battery")
    assert not verify_password({"password_hash": encoded}, "")


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "not-a-hash",
        "$2b$bad",
        "ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f",
    ],
)
def test_malformed_hash_is_rejected_not_crashed(malformed):
    assert verify_password({"password_hash": malformed}, "anything") is False


def test_long_passwords_are_not_truncated_at_72_bytes():
    base = "x" * 72
    encoded = hash_password(base + "TAIL-A")
    assert not verify_password({"password_hash": encoded}, base + "TAIL-B")
    assert verify_password({"password_hash": encoded}, base + "TAIL-A")


def test_registration_returns_an_opaque_session_token(client):
    response = _register(client, "new.user@example.com", name="New User")
    assert response.status_code == 201, response.text
    body = response.json()

    token = body["session_token"]
    assert len(token) >= 32
    assert token.count(".") != 2
    assert body["user_id"] not in token
    assert body["expires_in_seconds"] > 0

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user_id"] == body["user_id"]


def test_self_registration_cannot_grant_admin(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Escalation Attempt",
            "work_email": "escalate@example.com",
            "organization": "Acme",
            "password": LONG_PASSWORD,
            "confirm_password": LONG_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "analyst"

    headers = {"Authorization": f"Bearer {response.json()['session_token']}"}
    assert client.post("/model/train", headers=headers).status_code == 403


def test_duplicate_email_is_rejected(client):
    assert _register(client, "dup@example.com").status_code == 201
    assert _register(client, "dup@example.com").status_code == 400


def test_mismatched_confirmation_is_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Mismatch",
            "work_email": "mismatch@example.com",
            "organization": "Acme",
            "password": LONG_PASSWORD,
            "confirm_password": "a-different-long-password",
        },
    )
    assert response.status_code == 400


def test_short_password_is_rejected_before_reaching_the_store(client):
    assert _register(client, "short@example.com", password="short").status_code == 422


def test_storage_rejects_an_unknown_role():
    with pytest.raises(StorageError):
        storage.create_user(
            full_name="Role Probe",
            work_email="role.probe@example.com",
            organization="Acme",
            password=LONG_PASSWORD,
            role="superuser",
        )


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
        password=LONG_PASSWORD,
        full_name="Mixed",
        organization="Acme",
    )
    assert authenticate("mixedcase@example.com", LONG_PASSWORD)


def test_repeated_failures_are_throttled(client):
    _make_user("throttle@example.com")
    statuses = [
        client.post(
            "/auth/login",
            json={"email": "throttle@example.com", "password": f"wrong-guess-{n:03d}"},
        ).status_code
        for n in range(12)
    ]
    assert 429 in statuses, statuses

    locked = client.post(
        "/auth/login",
        json={"email": "throttle@example.com", "password": LONG_PASSWORD},
    )
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers


def test_throttle_is_per_account(client, analyst_headers):
    for n in range(12):
        client.post(
            "/auth/login",
            json={"email": "victim@example.com", "password": f"wrong-{n}"},
        )
    ok = client.post(
        "/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )
    assert ok.status_code == 200


def test_session_tokens_are_not_stored_in_the_clear(client, analyst_token):
    with storage._get_connection() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM sessions").fetchall()]

    assert rows
    assert all(analyst_token not in str(row.values()) for row in rows)
    assert any(row["token_hash"] == _token_fingerprint(analyst_token) for row in rows)


def test_logout_revokes_the_session_immediately(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client):
    user = _make_user("expiring@example.com")
    record = storage.create_session(user.user_id, ttl_seconds=1)

    with storage._get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET expires_at_utc = ? WHERE token_hash = ?",
            (
                storage._utc_iso(storage._utc_now() - timedelta(hours=1)),
                _token_fingerprint(record.session_token),
            ),
        )

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {record.session_token}"}
    )
    assert response.status_code == 401


def test_deleted_account_invalidates_its_open_session(client):
    user = _make_user("deleted@example.com")
    record = storage.create_session(user.user_id)
    headers = {"Authorization": f"Bearer {record.session_token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200

    with storage._get_connection() as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user.user_id,))

    assert client.get("/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "token",
    ["", "   ", "not-a-real-token", "a" * 64, "../../etc/passwd", "' OR 1=1 --"],
)
def test_garbage_tokens_are_rejected(client, token):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_authorization_header_is_rejected(client):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/logout").status_code == 401


def test_response_never_carries_the_password_hash(client, analyst_headers):
    body = client.get("/auth/me", headers=analyst_headers).json()
    assert "password_hash" not in body
    assert "password" not in body


def test_reset_request_never_returns_the_token(client):
    _make_user("reset@example.com")
    response = client.post(
        "/auth/password-reset/request", json={"work_email": "reset@example.com"}
    )
    assert response.status_code == 200
    assert "token" not in response.json()


def test_reset_request_does_not_reveal_whether_the_account_exists(client):
    known = client.post(
        "/auth/password-reset/request", json={"work_email": "reset@example.com"}
    )
    unknown = client.post(
        "/auth/password-reset/request", json={"work_email": "nobody@example.com"}
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_tokens_are_hashed_at_rest_and_single_use(client):
    _make_user("single.use@example.com")
    token = storage.create_password_reset("single.use@example.com")

    with storage._get_connection() as conn:
        stored = conn.execute("SELECT token_hash FROM password_resets").fetchall()
    assert all(row["token_hash"] != token for row in stored)

    assert storage.consume_password_reset(token, "a-brand-new-long-password") is True
    assert storage.consume_password_reset(token, "another-long-password-x") is False


def test_reset_revokes_every_open_session(client):
    _make_user("revoke@example.com")
    token = client.post(
        "/auth/login",
        json={"email": "revoke@example.com", "password": LONG_PASSWORD},
    ).json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200

    reset_token = storage.create_password_reset("revoke@example.com")
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "a-completely-new-password"},
    )
    assert response.status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_reset_rejects_a_weak_new_password(client):
    _make_user("weak.reset@example.com")
    reset_token = storage.create_password_reset("weak.reset@example.com")
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "short"},
    )
    assert response.status_code == 422


def test_reset_rejects_an_unknown_token(client):
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "n" * 40, "new_password": LONG_PASSWORD},
    )
    assert response.status_code == 400


def test_unauthenticated_caller_cannot_retrain_the_model(client):
    assert client.post("/model/train").status_code in (401, 403)


def test_analyst_token_cannot_reach_an_admin_endpoint(client, analyst_headers):
    assert client.post("/model/train", headers=analyst_headers).status_code == 403
    assert client.get("/model/datasets", headers=analyst_headers).status_code == 403


def test_revoked_admin_session_cannot_retrain(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/auth/logout", headers=headers)
    assert client.post("/model/train", headers=headers).status_code == 401


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
    assert "not found at" not in response.text


def test_dataset_registry_exposes_names_only(client, admin_headers):
    response = client.get("/model/datasets", headers=admin_headers)
    assert response.status_code == 200
    for name in response.json()["datasets"]:
        assert "/" not in name and "\\" not in name


@pytest.mark.parametrize("path", ["/health", "/model/status", "/personas"])
def test_public_endpoints_remain_public(client, path):
    assert client.get(path).status_code == 200


def test_sql_injection_in_login_does_not_bypass_authentication(client):
    response = client.post(
        "/auth/login",
        json={"email": "' OR '1'='1", "password": "' OR '1'='1' --"},
    )
    assert response.status_code == 401

    with storage._get_connection() as conn:
        assert isinstance(
            conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"], int
        )


def test_schema_constrains_roles_at_the_database_level():
    user = storage.get_user_by_email("analyst@example.com")
    if user is None:
        pytest.skip("analyst fixture not created in this run")

    with pytest.raises(sqlite3.IntegrityError):
        with storage._get_connection() as conn:
            conn.execute(
                "UPDATE memberships SET role = 'root' WHERE user_id = ?",
                (user.user_id,),
            )
