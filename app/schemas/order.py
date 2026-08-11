from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    product_id: int

    # Prevent zero or negative quantities.
    quantity: int = Field(
        ge=1,
        le=100,
    )


class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    total_cents: int
    idempotency_key: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )