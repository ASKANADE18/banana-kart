# BananaKart Backend Chronicles

## Episode 7: Banana Image Disaster

BananaKart now needs product images.

Storing large file data directly in PostgreSQL is possible, but object storage is a better fit for files such as images.

This episode introduces:

* Object storage
* Amazon S3
* Private buckets
* Presigned URLs
* Stable object keys
* Direct client-to-S3 file access
* Mocking external services in tests

---

## Implemented

* `image_key` added to the Product model
* Alembic migration for the new column
* Private S3 bucket
* Separate AWS profile for BananaKart
* S3 client using Boto3
* Presigned GET URL generation
* Product image endpoint
* Real S3 end-to-end test
* Automated tests with mocked S3 behavior

---

## Storage Design

PostgreSQL stores only the stable reference to the file.

Example:

```text
products table

id = 1
name = Banana
image_key = products/1/banana.jpg
```

The actual image bytes live in S3:

```text
S3 bucket
└── products
    └── 1
        └── banana.jpg
```

Memory:

```text
PostgreSQL
→ metadata / stable reference

S3
→ actual file bytes
```

---

## Why Object Storage?

Large files are different from normal relational data.

Keeping images in object storage avoids making PostgreSQL responsible for:

```text
large binary files
file transfer
file-serving bandwidth
larger database backups
```

The responsibilities stay separate:

```text
PostgreSQL
→ structured application data

S3
→ files
```

---

## Private S3 Bucket

The S3 bucket remains private.

Objects are not permanently exposed to the internet.

Instead, the backend generates temporary access when needed.

```text
Private object
     ↓
Backend authorizes request
     ↓
Presigned URL
     ↓
Temporary access
```

---

## Object Key vs Presigned URL

The database stores:

```text
products/1/banana.jpg
```

This is the S3 object key.

The database does not store the presigned URL.

```text
Object key
→ stable

Presigned URL
→ temporary
→ expires
```

When access is needed:

```text
image_key
   ↓
Boto3
   ↓
generate new presigned URL
```

---

## Product Image Endpoint

```http
GET /products/{product_id}/image
```

Example:

```http
GET /products/1/image
```

Flow:

```text
Client
   ↓
GET /products/1/image
   ↓
FastAPI route
   ↓
Depends(get_db)
   ↓
Load Product from PostgreSQL
   ↓
Read product.image_key
   ↓
generate_product_image_url()
   ↓
Boto3
   ↓
Generate temporary S3 URL
   ↓
ProductImageResponse
   ↓
Client
```

---

## Direct File Access

The image itself does not pass through FastAPI.

```text
FastAPI
→ controls access
→ generates temporary URL

Client
→ uses URL
→ downloads directly from S3
```

This avoids making the application server an unnecessary middleman for large file transfers.

---

## Presigned URL

The backend generates a URL similar to:

```text
https://...amazonaws.com/...?...signature...
```

The URL is valid only for a limited period.

Example:

```text
ExpiresIn = 3600
→ valid for 1 hour
```

Expiration affects only the temporary access URL.

The S3 object itself remains stored.

---

## AWS Project Separation

BananaKart uses its own AWS profile:

```text
bananakart
```

The local configuration points Boto3 to that profile.

Conceptually:

```text
BananaKart
   ↓
AWS_PROFILE=bananakart
   ↓
BananaKart IAM identity
   ↓
BananaKart S3 bucket
```

This keeps BananaKart separate from other AWS projects on the same machine.

---

## Code Flow

```text
GET /products/{id}/image
        ↓
products.py
        ↓
db.get(Product, id)
        ↓
product.image_key
        ↓
storage.py
        ↓
boto3.Session(...)
        ↓
S3 client
        ↓
generate_presigned_url()
        ↓
temporary URL
        ↓
ProductImageResponse
        ↓
JSON response
```

---

## Testing

The endpoint test uses the real FastAPI route and real test database, but mocks the external S3 helper.

```text
TestClient
   ↓
real route
   ↓
real Product lookup
   ↓
mocked S3 helper
   ↓
fake presigned URL
   ↓
assert response
```

This avoids requiring AWS during automated tests.

Memory:

```text
Mock the external dependency
not the whole application
```

---

## Real End-to-End Test

A real image was uploaded to S3 using:

```text
products/1/banana.jpg
```

The same key was stored in PostgreSQL.

Then:

```http
GET /products/1/image
```

returned a real presigned URL.

Opening that URL caused the browser to fetch the image directly from S3.

---

## Key Takeaways

```text
PostgreSQL
→ stores stable file reference

S3
→ stores actual file bytes

Object key
→ stable identifier

Presigned URL
→ temporary permission

Private bucket
→ objects are not permanently public

FastAPI
→ authorization

S3
→ storage + file transfer
```

---

## What Episode 7 Does Not Solve

The current implementation intentionally does not include:

```text
full presigned upload endpoint
multiple image records per product
image resizing
virus scanning
image processing
CDN delivery
automatic cleanup of unused objects
```

Those are production concerns outside the scope of this episode.

---

## Next Episode

### Episode 8: The Email Intern Quit

The next problem:

```text
A request should not have to wait for slow non-critical work.
```

Topics:

```text
BackgroundTasks
background processing
queues
SQS / Celery / Kafka concepts
```
