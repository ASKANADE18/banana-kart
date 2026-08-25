# BananaKart — Episode 9: Bot Army

Episode 9 adds Redis-backed rate limiting to protect the API from excessive traffic and repeated login attempts.

The episode implements and compares three rate-limiting algorithms:

- Fixed Window
- Sliding Window
- Token Bucket

The `/auth/login` endpoint currently uses Token Bucket.

---

## What Was Implemented

- Added `app/rate_limit.py`
- Added Redis-backed Fixed Window rate limiting
- Added Redis-backed Sliding Window rate limiting
- Added Redis-backed Token Bucket rate limiting
- Added combined IP-based and email-based rate limiting to `/auth/login`
- Added `429 Too Many Requests` responses
- Added fail-open behavior when Redis is unavailable
- Added automated tests for all three algorithms
- Added test cleanup for Redis rate-limit keys

---

## Login Request Flow

```text
POST /auth/login
        ↓
Check rate limit in Redis
        ↓
    Allowed?
   ┌────┴────┐
   │         │
  No        Yes
   │         │
 429      Continue
             ↓
       Find user
             ↓
       Verify password
             ↓
       Generate JWT
```

Rate limiting runs before database lookup and password verification so blocked requests do not reach more expensive authentication work.

---

## Fixed Window

Fixed Window stores a request counter in Redis.

```text
Request
   ↓
Redis INCR
   ↓
Count <= limit?
   ↓
Allow / Reject
```

The Redis key expires after the configured window.

Example:

```text
Limit: 5 requests / 60 seconds
```

The sixth request is rejected with `429`.

### Limitation

Fixed Window can allow bursts around window boundaries.

---

## Sliding Window

Sliding Window stores recent request timestamps in a Redis sorted set.

For each request:

```text
Remove expired timestamps
        ↓
Count active requests
        ↓
Limit reached?
   ┌────┴────┐
   │         │
  Yes        No
   │         │
Reject    Add timestamp
             ↓
           Allow
```

This checks the actual rolling time window instead of a fixed clock window.

---

## Token Bucket

Token Bucket maintains:

```text
tokens
last_refill_time
```

Example configuration:

```text
capacity = 5
refill = 1 token every 10 seconds
```

Each request consumes one token.

```text
Request
   ↓
Load bucket
   ↓
Calculate refill
   ↓
Add available tokens
   ↓
Cap at capacity
   ↓
Token available?
   ┌────┴────┐
   │         │
  No        Yes
   │         │
 429      Consume 1
             ↓
           Allow
```

The bucket capacity controls the maximum burst size while the refill interval controls how quickly request capacity returns.

---

## Login Rate Limiting

The `/auth/login` endpoint currently uses Token Bucket rate limiting with two independent Redis keys:

```text
IP-based limit
+
Email-based limit
```

The email is normalized before the rate-limit check:

```python
email = form_data.username.strip().lower()
```

### IP-Based Limit

```python
ip_allowed = check_token_bucket_rate_limit(
    key=f"rate_limit:token:login:ip:{client_ip}",
    capacity=50,
    refill_interval_seconds=2,
)
```

The IP limiter is intentionally more permissive.

Multiple legitimate users may share the same public IP when using:

- home or office Wi-Fi
- NAT
- university networks
- mobile networks
- VPNs or proxies

For example:

```text
User A ─┐
User B ─┼── Shared Network ── Same Public IP ── BananaKart
User C ─┘
```

A strict IP-only limit could therefore block legitimate users on the same network.

The IP bucket is used as broader protection against a single source sending a large amount of login traffic.

### Email-Based Limit

```python
email_allowed = check_token_bucket_rate_limit(
    key=f"rate_limit:token:login:email:{email}",
    capacity=5,
    refill_interval_seconds=10,
)
```

The email limiter is stricter because it protects a specific account from repeated login attempts.

This also helps when an attacker changes IP addresses but continues targeting the same account.

### Combined Flow

```text
POST /auth/login
        ↓
Normalize email
        ↓
Check IP bucket
        ↓
IP blocked?
   Yes → 429
        ↓ No
Check email bucket
        ↓
Email blocked?
   Yes → 429
        ↓ No
Query PostgreSQL
        ↓
Verify password
        ↓
Generate JWT
```

The two limits solve different problems:

```text
IP limit
→ protects against high-volume traffic from one source

Email limit
→ protects one account from repeated login attempts
```

The current limits are learning/demo values. Real production limits would be tuned using actual traffic and abuse patterns.

---

## Why Redis

Rate-limit state must be shared when multiple FastAPI instances are running.

```text
              Load Balancer
                   ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
    Server 1   Server 2   Server 3
        \          |          /
                 Redis
```

Using local Python counters would give each server an independent request count.

Redis provides one shared rate-limit state across application instances.

---

## Redis Failure

Rate limiting uses fail-open behavior:

```python
except RedisError:
    return True
```

If Redis is unavailable, the request continues without rate limiting instead of making the main API unavailable.

---

## Testing

Rate-limit tests cover:

- Fixed Window allowing requests up to the configured limit
- Fixed Window rejecting the next request
- Sliding Window rejecting requests after the rolling limit is reached
- Token Bucket blocking login when the bucket is empty
- Email-based rate limiting independently protecting an account
- Existing authentication and order functionality continuing to work

Run the full test suite:

```bash
./.venv/bin/python -m pytest -v
```

---

## Files Changed

```text
app/
├── api/
│   └── routes/
│       └── auth.py
└── rate_limit.py

tests/
├── conftest.py
└── test_auth.py
```

---

## Algorithm Comparison

| Algorithm | Storage | Main Tradeoff |
|---|---|---|
| Fixed Window | Counter + TTL | Simple, but boundary bursts are possible |
| Sliding Window | Sorted set of timestamps | More accurate, but requires more Redis operations |
| Token Bucket | Tokens + refill timestamp | Allows controlled bursts with gradual refill |

---

## Production Note

The learning implementation keeps the algorithms intentionally simple.

Fixed Window uses Redis `INCR`, which is atomic.

Sliding Window and Token Bucket perform multiple Redis operations. In a production distributed system, the complete rate-limit decision should be made atomic, commonly with a Redis Lua script or another transactional approach.

---

## Episode Result

BananaKart now has a Redis-backed traffic protection layer that can reject excessive login requests before they reach database and password-verification work.
