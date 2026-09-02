# BananaKart — Episode 10: Nobody Knows Production Is Down

Episode 10 adds basic observability and health checks so BananaKart can provide useful information when requests become slow, fail, or when an application instance is not ready to serve traffic.

---

## What Was Implemented

- Request logging middleware
- HTTP method, path, status code, and request duration logging
- Unique request IDs
- `X-Request-ID` response header
- Request ID stored in `request.state`
- Unexpected exception logging with traceback
- Global safe `500 Internal Server Error` response
- Liveness health check
- PostgreSQL readiness health check
- Automated health-check tests

---

## Request Logging Middleware

The middleware runs around every HTTP request.

```text
Client
  ↓
Middleware
  ├─ generate request ID
  ├─ start timer
  ↓
FastAPI route
  ↓
Middleware
  ├─ calculate duration
  ├─ log status
  └─ add X-Request-ID header
  ↓
Client
```

Example log:

```text
INFO | request_id=a3a879d8-... | POST /auth/login | status=200 | duration=126.05ms
```

This provides useful request-level information without adding logging code to every route.

---

## Request IDs

Each incoming request receives a UUID:

```python
request_id = str(uuid.uuid4())
request.state.request_id = request_id
```

The ID is included in application logs:

```text
request_id=a3a879d8-...
```

and returned to the client:

```text
X-Request-ID: a3a879d8-...
```

A request ID makes it easier to find all logs related to one specific request.

Routes can access the same ID through:

```python
request.state.request_id
```

---

## Request Duration

The middleware measures total request duration using:

```python
start_time = time.perf_counter()
```

After the route finishes:

```python
duration_ms = (
    time.perf_counter() - start_time
) * 1000
```

This helps identify slow endpoints.

Example:

```text
GET /users/me    → 12.57ms
POST /auth/login → 126.05ms
```

---

## Unexpected Exceptions

Expected API errors such as `401`, `404`, `409`, `422`, and `429` are normal application responses.

Unexpected Python exceptions require different handling.

The middleware logs them using:

```python
logger.exception(...)
```

`logger.exception()` records both:

```text
error message
+
Python traceback
```

The exception is then allowed to continue to the global exception handler.

---

## Global Exception Handler

Unexpected errors return a safe response to the client:

```json
{
  "detail": "Internal server error"
}
```

The client receives:

```text
500 Internal Server Error
```

while the developer logs retain the traceback needed for debugging.

```text
Client
→ safe error message

Logs
→ detailed traceback
```

Internal exception details are not exposed in the API response.

---

## Log Levels

The basic log levels used in backend applications include:

```text
INFO
→ normal important events

WARNING
→ unusual or degraded behavior

ERROR
→ an operation failed
```

Sensitive values such as passwords, JWTs, API keys, and secrets should never be written to logs.

---

## Health Checks

BananaKart exposes separate liveness and readiness checks.

### Liveness

```text
GET /health/live
```

Response:

```json
{
  "status": "ok"
}
```

Liveness answers:

```text
Is the FastAPI application process alive?
```

A successful liveness check returns `200 OK`.

---

### Readiness

```text
GET /health/ready
```

The readiness endpoint performs a small PostgreSQL check:

```sql
SELECT 1;
```

If PostgreSQL is reachable:

```json
{
  "status": "ready"
}
```

with:

```text
200 OK
```

If PostgreSQL is unavailable:

```text
503 Service Unavailable
```

Readiness answers:

```text
Should this application instance currently receive traffic?
```

---

## Liveness vs Readiness

```text
Liveness
→ Is this process alive?

Readiness
→ Can this instance actually serve application traffic?
```

Example:

```text
FastAPI running      ✅
PostgreSQL running   ❌

/health/live  → 200
/health/ready → 503
```

A temporary database outage should make the instance not ready without implying that the FastAPI process itself must be restarted.

Redis is not included in BananaKart's readiness check because Redis-dependent functionality was designed to degrade gracefully when Redis is unavailable.

---

## Observability Concepts

Episode 10 also introduced the three main observability signals.

### Logs

Detailed records of individual events.

```text
What happened?
```

Example:

```text
POST /orders failed with a database exception
```

### Metrics

Aggregated measurements over time.

```text
How is the system behaving overall?
```

Examples:

```text
request count
error rate
p95 latency
CPU usage
memory usage
```

### Traces

Follow one request through multiple components.

```text
Where did this request spend its time?
```

Example:

```text
POST /orders              820ms
├── authentication         20ms
├── PostgreSQL SELECT     110ms
├── PostgreSQL COMMIT     640ms
└── Redis                  10ms
```

Distributed tracing was discussed conceptually but was not implemented in this episode.

---

## RED Monitoring Model

A useful API monitoring model is RED:

```text
R = Rate
    requests being received

E = Errors
    requests failing

D = Duration
    time requests take
```

A system can still have a performance problem even when requests return successfully.

```text
200 in 100ms
→ healthy response

200 in 8 seconds
→ successful but slow

500 in 20ms
→ fast but failed
```

---

## Testing

Health checks are covered in:

```text
tests/test_health.py
```

Tests verify:

```text
GET /health/live
→ 200
→ {"status": "ok"}

GET /health/ready
→ 200 when PostgreSQL is available
→ {"status": "ready"}
```

Run the full test suite with:

```bash
./.venv/bin/python -m pytest -v
```

---

## Files Changed

```text
app/
└── main.py

tests/
└── test_health.py
```

---

## Episode Result

BananaKart can now:

```text
observe incoming requests
        ↓
measure request duration
        ↓
correlate requests with request IDs
        ↓
log unexpected failures with tracebacks
        ↓
return safe 500 responses
        ↓
report application liveness
        ↓
report PostgreSQL readiness
```

Episode 10 adds the basic observability and health-check foundation needed to understand whether the backend is running correctly and whether an application instance should receive traffic.
