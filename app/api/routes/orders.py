from typing import Annotated
import json

from app.cache import redis_client, clear_user_order_cache
from redis.exceptions import RedisError

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
from fastapi import Query


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
    product = db.scalar(
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
        clear_user_order_cache(current_user.id)

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

@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    cache_key = (
        f"orders:user:{current_user.id}:"
        f"limit:{limit}:offset:{offset}"
    )

    cached_orders = None

    try:
        cached_orders = redis_client.get(cache_key)
    except RedisError:
        pass

    if cached_orders is not None:
        return json.loads(cached_orders)
    
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    orders_data = [
        OrderResponse.model_validate(order).model_dump(mode="json")
        for order in orders
    ]

    try:
        redis_client.setex(
            cache_key,
            60,
            json.dumps(orders_data),
        )
    except RedisError:
        pass

    return orders_data