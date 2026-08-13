import boto3

from app.config import settings


session = boto3.Session(
    profile_name=settings.aws_profile,
    region_name=settings.aws_region,
)

s3_client = session.client("s3")


def generate_product_image_url(image_key: str) -> str:
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": image_key,
        },
        ExpiresIn=3600,
    )