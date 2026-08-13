from app.models.product import Product
from concurrent.futures import ThreadPoolExecutor

from redis.exceptions import RedisError

from app.cache import redis_client


def create_product(db_session, stock_quantity=100):
    """
    Create one Banana product for order tests.
    """

    product = Product(
        name="Banana",
        price_cents=50,
        stock_quantity=stock_quantity,
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def register_and_login(client):
    """
    Register a user and return a valid JWT.
    """

    client.post(
        "/users",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "password": "banana-secret-123",
        },
    )

    login_response = client.post(
        "/auth/login",
        data={
            "username": "bob@example.com",
            "password": "banana-secret-123",
        },
    )

    return login_response.json()["access_token"]


def test_create_order_reduces_stock(
    client,
    db_session,
):
    product = create_product(db_session)
    token = register_and_login(client)

    response = client.post(
        "/orders",
        json={
            "product_id": product.id,
            "quantity": 57,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "order-001",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["quantity"] == 57
    assert body["total_cents"] == 2850

    db_session.refresh(product)

    assert product.stock_quantity == 43


def test_same_idempotency_key_does_not_create_duplicate(
    client,
    db_session,
):
    product = create_product(db_session)
    token = register_and_login(client)

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "order-001",
    }

    body = {
        "product_id": product.id,
        "quantity": 57,
    }

    first_response = client.post(
        "/orders",
        json=body,
        headers=headers,
    )

    second_response = client.post(
        "/orders",
        json=body,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    # Retry should return the same order.
    assert (
        first_response.json()["id"]
        == second_response.json()["id"]
    )

    db_session.refresh(product)

    # Stock should only be reduced once.
    assert product.stock_quantity == 43


def test_order_rejected_when_stock_is_insufficient(
    client,
    db_session,
):
    product = create_product(
        db_session,
        stock_quantity=10,
    )

    token = register_and_login(client)

    response = client.post(
        "/orders",
        json={
            "product_id": product.id,
            "quantity": 57,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "too-many-bananas",
        },
    )

    assert response.status_code == 409

    db_session.refresh(product)

    assert product.stock_quantity == 10

def test_only_one_user_can_buy_last_item(client, db_session):
    # Arrange: only one banana exists
    product = create_product(db_session, stock_quantity=1)

    # Create Bob
    client.post(
        "/users",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "password": "banana-secret-123",
        },
    )

    bob_login = client.post(
        "/auth/login",
        data={
            "username": "bob@example.com",
            "password": "banana-secret-123",
        },
    )

    bob_token = bob_login.json()["access_token"]

    # Create Alice
    client.post(
        "/users",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "banana-secret-123",
        },
    )

    alice_login = client.post(
        "/auth/login",
        data={
            "username": "alice@example.com",
            "password": "banana-secret-123",
        },
    )

    alice_token = alice_login.json()["access_token"]

    def buy(token, key):
        return client.post(
            "/orders",
            json={
                "product_id": product.id,
                "quantity": 1,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": key,
            },
        )

    # Act: Bob and Alice send requests concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        bob_future = executor.submit(
            buy,
            bob_token,
            "bob-last-banana",
        )

        alice_future = executor.submit(
            buy,
            alice_token,
            "alice-last-banana",
        )

        responses = [
            bob_future.result(),
            alice_future.result(),
        ]

    # Assert
    status_codes = sorted(
        response.status_code
        for response in responses
    )

    assert status_codes == [201, 409]

    db_session.refresh(product)
    assert product.stock_quantity == 0

def test_get_orders_returns_current_users_orders(
    client,
    db_session,
):
    product = create_product(db_session, stock_quantity=100)

    token = register_and_login(client)

    for i in range(3):
        client.post(
            "/orders",
            json={
                "product_id": product.id,
                "quantity": 1,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"order-{i}",
            },
        )

    response = client.get(
        "/orders?limit=20&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 3

def test_get_orders_pagination(
    client,
    db_session,
):
    product = create_product(db_session, stock_quantity=100)

    token = register_and_login(client)

    for i in range(5):
        client.post(
            "/orders",
            json={
                "product_id": product.id,
                "quantity": 1,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"page-order-{i}",
            },
        )

    response = client.get(
        "/orders?limit=2&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_orders_rejects_invalid_limit(
    client,
):
    token = register_and_login(client)

    response = client.get(
        "/orders?limit=1000",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 422

def test_get_orders_populates_cache(
    client,
    db_session,
):
    product = create_product(db_session, stock_quantity=100)
    token = register_and_login(client)

    client.post(
        "/orders",
        json={
            "product_id": product.id,
            "quantity": 1,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "cache-order-1",
        },
    )

    redis_client.flushdb()

    response = client.get(
        "/orders?limit=20&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    keys = list(
        redis_client.scan_iter(
            match="orders:user:*"
        )
    )

    assert len(keys) == 1

def test_create_order_invalidates_cache(
    client,
    db_session,
):
    product = create_product(db_session, stock_quantity=100)
    token = register_and_login(client)

    # Build cache
    client.get(
        "/orders?limit=20&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    keys_before = list(
        redis_client.scan_iter(
            match="orders:user:*"
        )
    )

    assert len(keys_before) > 0

    # Create a new order
    response = client.post(
        "/orders",
        json={
            "product_id": product.id,
            "quantity": 1,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "invalidate-order-1",
        },
    )

    assert response.status_code == 201

    keys_after = list(
        redis_client.scan_iter(
            match="orders:user:*"
        )
    )

    assert len(keys_after) == 0

def test_get_orders_works_when_redis_is_down(
        client,
        db_session,
        monkeypatch,
    ):
    product = create_product(db_session, stock_quantity=100)
    token = register_and_login(client)

    client.post(
        "/orders",
        json={
            "product_id": product.id,
            "quantity": 1,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "redis-down-order",
        },
    )

    def broken_get(*args, **kwargs):
        raise RedisError("Redis unavailable")

    def broken_setex(*args, **kwargs):
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        redis_client,
        "get",
        broken_get,
    )

    monkeypatch.setattr(
        redis_client,
        "setex",
        broken_setex,
    )

    response = client.get(
        "/orders?limit=20&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1