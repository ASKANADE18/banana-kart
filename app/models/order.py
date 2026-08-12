from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from sqlalchemy import Index, UniqueConstraint


class Order(Base):

    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_order_user_idempotency",
        ),
        Index(
        "ix_orders_user_created_at",
        "user_id",
        "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    total_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

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