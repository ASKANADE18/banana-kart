from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductImageResponse
from app.storage import generate_product_image_url

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.get(
    "/{product_id}/image",
    response_model=ProductImageResponse,
)
def get_product_image(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.image_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product image not found",
        )

    image_url = generate_product_image_url(
        product.image_key
    )

    return ProductImageResponse(
        image_url=image_url
    )