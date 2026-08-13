# BananaKart Backend Chronicles

## Episode 6: Redis Saves the Company

BananaKart now has paginated order history, but repeated reads still hit PostgreSQL every time.

This episode introduces Redis as a cache for frequently requested order-history data.

The focus is on:

* Cache-aside pattern
* TTL
* Cache invalidation
* Graceful fallback when Redis is unavailable

---

## Implemented

* Redis container with Docker Compose
* Python Redis client
* Order-history caching
* Pagination-aware cache keys
* 60-second TTL
* Cache invalidation after successful order creation
* PostgreSQL fallback when Redis is unavailable
* Automated Redis behavior tests

---

## Why Redis?

Without caching:

```text
GET /orders
   ↓
PostgreSQL

GET /orders again
   ↓
PostgreSQL again
```

Even if the data has not changed, the database performs the same query repeatedly.

With Redis:

```text
GET /orders
   ↓
Redis
   ↓
cache hit?
 ├── yes → return cached data
 └── no  → PostgreSQL
            ↓
          cache result
            ↓
          return response
```

Redis improves read performance, but PostgreSQL remains the source of truth.

```text
PostgreSQL
→ authoritative data

Redis
→ temporary cached copy
```

---

## Cache-Aside Pattern

The order-history endpoint follows the cache-aside pattern.

```text
GET /orders
   ↓
Check Redis
   ↓
Cache hit?
 ├── yes
 │    ↓
 │ return cached data
 │
 └── no
      ↓
    Query PostgreSQL
      ↓
    Store result in Redis
      ↓
    Return response
```

The application controls when data is read from or written to the cache.

Memory:

```text
Cache-aside
→ cache first
→ database on miss
```

---

## Cache Keys

Order history depends on:

* authenticated user
* `limit`
* `offset`

So the cache key includes all of them.

Example:

```text
orders:user:42:limit:20:offset:0
```

This prevents different requests from incorrectly sharing the same cached response.

For example:

```text
GET /orders?limit=20&offset=0
GET /orders?limit=2&offset=0
```

must use different cache entries.

Memory:

```text
Cache key
→ include inputs that affect the response
```

---

## TTL

Cached order history is stored with a 60-second TTL.

```text
TTL
→ Time To Live
```

Example:

```text
orders:user:42:limit:20:offset:0
TTL = 60 seconds
```

After the TTL expires, Redis automatically removes the cached value.

The next request becomes a cache miss and reloads fresh data from PostgreSQL.

---

## Cache Invalidation

Cached data can become stale after a write.

Example:

```text
Redis
→ 5 cached orders

POST /orders succeeds

PostgreSQL
→ now has 6 orders
```

If the cache is not invalidated, the next GET could incorrectly return the old 5-order response.

After a successful order creation:

```text
POST /orders
   ↓
Database transaction
   ↓
db.commit()
   ↓
Delete user's order-history cache
```

The next GET then follows:

```text
Redis miss
   ↓
PostgreSQL
   ↓
fresh order history
   ↓
cache rebuilt
```

Memory:

```text
Write succeeds
→ invalidate stale cache
```

---

## Why Invalidate After Commit?

The database is updated first:

```text
db.commit()
   ↓
database write succeeded
   ↓
clear Redis cache
```

The cache is not deleted before the database commit.

If the database write fails, the existing cache may still represent valid data.

```text
DB commit first
Cache invalidation second
```

---

## Pagination-Aware Invalidation

A user can have multiple cached order-history pages.

Example:

```text
orders:user:42:limit:20:offset:0
orders:user:42:limit:20:offset:20
orders:user:42:limit:2:offset:0
```

After an order is created, all order-history cache entries for that user are removed.

Conceptually:

```text
orders:user:42:*
```

This ensures every cached page is rebuilt from fresh PostgreSQL data.

---

## Redis Failure

Redis is an optimization, not the source of truth.

If Redis becomes unavailable:

```text
GET /orders
   ↓
Redis connection fails
   ↓
RedisError caught
   ↓
PostgreSQL queried
   ↓
response still returned
```

The API remains functional.

```text
Redis failure
→ performance degradation

PostgreSQL failure
→ availability/correctness problem
```

Memory:

```text
Cache failure should not break core reads.
```

---

## Code Flow

```text
GET /orders
        ↓
FastAPI validates limit + offset
        ↓
Depends(get_current_user)
        ↓
Authenticated User
        ↓
Depends(get_db)
        ↓
SQLAlchemy Session
        ↓
Build Redis cache key
        ↓
redis_client.get()
        ↓
Cache hit?
   ├── yes
   │     ↓
   │   json.loads()
   │     ↓
   │   return response
   │
   └── no / Redis error
         ↓
       PostgreSQL query
         ↓
       SQLAlchemy Order objects
         ↓
       OrderResponse
         ↓
       JSON-serializable data
         ↓
       redis_client.setex()
         ↓
       return response
```

---

## Write Flow

```text
POST /orders
        ↓
Idempotency check
        ↓
Lock Product row
        ↓
Check inventory
        ↓
Create Order
+
Reduce stock
        ↓
db.commit()
        ↓
PostgreSQL updated
        ↓
clear_user_order_cache()
        ↓
Return OrderResponse
```

---

## Redis Commands Used

Set and expire a value:

```text
SETEX
```

Conceptually:

```text
store value
+
expire after TTL
```

Read cached data:

```text
GET
```

Find matching user cache keys:

```text
SCAN
```

Delete stale cache:

```text
DELETE
```

---

## JSON Serialization

Redis stores strings rather than SQLAlchemy ORM objects.

Order objects are converted into response-shaped data before caching.

Conceptually:

```text
SQLAlchemy Order
   ↓
OrderResponse
   ↓
Python dictionary
   ↓
json.dumps()
   ↓
Redis
```

When reading:

```text
Redis JSON string
   ↓
json.loads()
   ↓
Python data
   ↓
FastAPI response
```

---

## Graceful Degradation

Redis access is wrapped in Redis error handling.

```text
try Redis
   ↓
works?
 ├── yes → use cache
 └── no  → continue with PostgreSQL
```

This prevents Redis from becoming a single point of failure for order-history reads.

---

## Tests

Episode 6 tests verify:

* GET order history populates Redis
* Creating an order invalidates the user's cache
* Order history still works when Redis raises an error
* Previous authentication, transaction, idempotency, locking, pagination, and indexing behavior remains intact

Run:

```bash
./.venv/bin/python -m pytest -v
```

Expected:

```text
22 passed
```

---

## Key Takeaways

```text
PostgreSQL
→ source of truth

Redis
→ temporary fast cache

Cache-aside
→ check cache first, database on miss

TTL
→ automatically expire cached data

Cache invalidation
→ remove stale cache after writes

Graceful degradation
→ Redis failure should not break core reads
```

---

## What Episode 6 Does Not Solve

The current cache implementation is intentionally simple.

Production systems may also need to consider:

```text
cache stampede
distributed invalidation
cache warming
memory limits
eviction policies
Redis clustering
```

Those concerns are outside the scope of this episode.

---

## Next Episode

### Episode 7: Banana Image Disaster

The next problem involves storing and serving files.

Topics:

```text
Object storage
S3
Presigned URLs
Public vs private files
```
