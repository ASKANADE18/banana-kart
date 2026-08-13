from pydantic import BaseModel


class ProductImageResponse(BaseModel):
    image_url: str