from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.core.security import create_access_token

def register_user(client):
    """
    Create a user that authentication tests can log in as.

    Each test receives a fresh test database, so the user must
    be registered inside the test itself.
    """

    return client.post(
        "/users",
        json={
            "name": "Ashwini Kanade",
            "email": "ashwini@example.com",
            "phone_number": "8625880595",
            "password": "banana-secret-123",
        },
    )


def login_user(client):
    """
    Log in using OAuth2 form data and return the response.

    Notice that login uses `data`, not `json`, because
    OAuth2PasswordRequestForm expects form fields.
    """

    return client.post(
        "/auth/login",
        data={
            "username": "ashwini@example.com",
            "password": "banana-secret-123",
        },
    )


def test_login_returns_access_token(client):
    register_response = register_user(client)
    assert register_response.status_code == 201

    login_response = login_user(client)

    assert login_response.status_code == 200

    response_body = login_response.json()

    assert "access_token" in response_body
    assert response_body["token_type"] == "bearer"
    assert response_body["access_token"].count(".") == 2


def test_login_rejects_incorrect_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        data={
            "username": "ashwini@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown@example.com",
            "password": "banana-secret-123",
        },
    )

    assert response.status_code == 401

    # Unknown email and incorrect password return the same public message.
    assert response.json() == {
        "detail": "Invalid email or password"
    }


def test_users_me_requires_authentication(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_authenticated_user_can_read_own_profile(client):
    register_user(client)
    login_response = login_user(client)

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
    )

    assert response.status_code == 200

    response_body = response.json()

    assert response_body["name"] == "Ashwini Kanade"
    assert response_body["email"] == "ashwini@example.com"

    # Sensitive password information must never be returned.
    assert "password" not in response_body
    assert "hashed_password" not in response_body


def test_users_me_rejects_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer definitely-not-a-real-jwt"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }


def test_users_me_rejects_expired_token(client):
    """
    A correctly signed token must still be rejected after it expires.
    """

    expired_payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }

def test_users_me_rejects_token_without_subject(client):
    """
    A token without `sub` does not identify any user.
    """

    payload = {
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }

    token_without_subject = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token_without_subject}"
        },
    )

    assert response.status_code == 401

def test_users_me_rejects_token_for_nonexistent_user(client):
    """
    A valid JWT is not enough if its user no longer exists
    in PostgreSQL.
    """

    token = create_access_token(
        subject="999999"
    )

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }

def test_fixed_window_rate_limit_blocks_sixth_request(monkeypatch):
    from app import rate_limit

    counts = {}

    def fake_incr(key):
        counts[key] = counts.get(key, 0) + 1
        return counts[key]

    def fake_expire(key, seconds):
        return True

    monkeypatch.setattr(
        rate_limit.redis_client,
        "incr",
        fake_incr,
    )

    monkeypatch.setattr(
        rate_limit.redis_client,
        "expire",
        fake_expire,
    )

    key = "rate_limit:fixed:test"

    for _ in range(5):
        allowed = rate_limit.check_fixed_window_rate_limit(
            key=key,
            limit=5,
            window_seconds=60,
        )
        assert allowed is True

    allowed = rate_limit.check_fixed_window_rate_limit(
        key=key,
        limit=5,
        window_seconds=60,
    )

    assert allowed is False

def test_sliding_window_rate_limit_blocks_sixth_request(monkeypatch):
    from app import rate_limit

    state = []

    def fake_time():
        return 1000.0

    def fake_zremrangebyscore(key, min_score, max_score):
        state[:] = [
            timestamp
            for timestamp in state
            if timestamp > max_score
        ]

    def fake_zcard(key):
        return len(state)

    def fake_zadd(key, mapping):
        for score in mapping.values():
            state.append(score)

    def fake_expire(key, seconds):
        return True

    monkeypatch.setattr(rate_limit.time, "time", fake_time)
    monkeypatch.setattr(rate_limit.redis_client, "zremrangebyscore", fake_zremrangebyscore)
    monkeypatch.setattr(rate_limit.redis_client, "zcard", fake_zcard)
    monkeypatch.setattr(rate_limit.redis_client, "zadd", fake_zadd)
    monkeypatch.setattr(rate_limit.redis_client, "expire", fake_expire)

    key = "rate_limit:sliding:test"

    for _ in range(5):
        allowed = rate_limit.check_sliding_window_rate_limit(
            key=key,
            limit=5,
            window_seconds=60,
        )
        assert allowed is True

    allowed = rate_limit.check_sliding_window_rate_limit(
        key=key,
        limit=5,
        window_seconds=60,
    )

    assert allowed is False

def test_token_bucket_rate_limit_blocks_when_empty(
    client,
    monkeypatch,
):
    calls = {"count": 0}

    def fake_token_bucket_rate_limit(
        key: str,
        capacity: int,
        refill_interval_seconds: int,
    ) -> bool:
        calls["count"] += 1
        return calls["count"] <= 5

    monkeypatch.setattr(
        "app.api.routes.auth.check_token_bucket_rate_limit",
        fake_token_bucket_rate_limit,
    )

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={
                "username": "wrong@example.com",
                "password": "wrong-password",
            },
        )

        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        data={
            "username": "wrong@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 429