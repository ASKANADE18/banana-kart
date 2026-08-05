from fastapi.testclient import TestClient


# Reuse one valid request body across multiple tests.
VALID_USER = {
    "name": "Ashwini Kanade",
    "email": "ashwini@example.com",
    "phone_number": "+1-201-555-0123",
    "password": "banana-secret-123",
}


def test_create_user_successfully(client: TestClient) -> None:
    """
    A valid signup request should create a user and return safe data.
    """

    response = client.post(
        "/users",
        json=VALID_USER,
    )

    assert response.status_code == 201

    data = response.json()

    assert isinstance(data["id"], int)
    assert data["name"] == "Ashwini Kanade"
    assert data["email"] == "ashwini@example.com"
    assert data["phone_number"] == "+1-201-555-0123"
    assert "created_at" in data
    assert "updated_at" in data

    # Sensitive information must never appear in the API response.
    assert "password" not in data
    assert "hashed_password" not in data


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    """
    Two accounts should not be allowed to use the same email.
    """

    first_response = client.post(
        "/users",
        json=VALID_USER,
    )

    second_response = client.post(
        "/users",
        json=VALID_USER,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert second_response.json() == {
        "detail": "Email is already registered",
    }


def test_invalid_registration_is_rejected(client: TestClient) -> None:
    """
    FastAPI should reject invalid data before the route creates a user.
    """

    invalid_user = {
        "name": "A",
        "email": "not-an-email",
        "phone_number": None,
        "password": "123",
    }

    response = client.post(
        "/users",
        json=invalid_user,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    # Each validation error includes the field location.
    invalid_fields = {
        error["loc"][-1]
        for error in errors
    }

    assert "name" in invalid_fields
    assert "email" in invalid_fields
    assert "password" in invalid_fields