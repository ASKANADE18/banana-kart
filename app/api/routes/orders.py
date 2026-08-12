from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database import get_db
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,

    # Client generates this key.
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key"),
    ],

    # Episode 2:
    # JWT tells us which user is placing the order.
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],

    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> Order:
    """
    Create an order safely.

    Episode 3 concepts:
    1. Idempotency prevents duplicate orders.
    2. One transaction keeps order + inventory changes atomic.
    """

    # ---------------------------------------------------------
    # 1. IDEMPOTENCY CHECK
    # ---------------------------------------------------------
    # Did this user already send this logical request?
    existing_order = db.scalar(
        select(Order).where(
            Order.user_id == current_user.id,
            Order.idempotency_key == idempotency_key,
        )
    )

    if existing_order is not None:
        # Same request retry.
        # Do NOT create another order.
        return existing_order

    # ---------------------------------------------------------
    # 2. FIND PRODUCT
    # ---------------------------------------------------------
    product = db.get(
        select(Product)
        .where(Product.id == order_data.product_id)
        .with_for_update()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # ---------------------------------------------------------
    # 3. CHECK INVENTORY
    # ---------------------------------------------------------
    if product.stock_quantity < order_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough stock",
        )

    # Calculate price on the backend.
    total_cents = (
        product.price_cents
        * order_data.quantity
    )

    # ---------------------------------------------------------
    # 4. BEGIN BUSINESS OPERATION
    # ---------------------------------------------------------

    new_order = Order(
        user_id=current_user.id,
        product_id=product.id,
        quantity=order_data.quantity,
        total_cents=total_cents,
        idempotency_key=idempotency_key,
    )

    db.add(new_order)

    # Second database change:
    product.stock_quantity -= order_data.quantity

    try:
        # Both changes are committed together:
        #
        # 1. INSERT order
        # 2. UPDATE product stock
        #
        # This is our transaction.
        db.commit()

    except IntegrityError:
        db.rollback()

        # Another identical request may have reached the DB
        # at almost the same time.
        existing_order = db.scalar(
            select(Order).where(
                Order.user_id == current_user.id,
                Order.idempotency_key == idempotency_key,
            )
        )

        if existing_order is not None:
            return existing_order

        raise

    db.refresh(new_order)

    return new_order