# BananaKart Backend Chronicles

## Episode 3: Bob Bought 57 Bananas

Bob can register and authenticate. Now he wants to buy 57 bananas.

This episode focuses on two backend reliability concepts:

- **Transactions** — prevent partial database updates
- **Idempotency** — prevent duplicate operations caused by retries

---

## Order Flow

```text
Authenticated user
        ↓
POST /orders
        ↓
Check idempotency key
        ↓
Find product
        ↓
Check stock
        ↓
Create order
        +
Reduce inventory
        ↓
COMMIT
```

If something fails:

```text
ROLLBACK
→ no partial changes remain
```

---

## Transaction

Creating the order and reducing stock must behave as one operation.

```text
Create Order ✅
Reduce Stock ❌
        ↓
ROLLBACK
        ↓
Neither change is persisted
```

**Transaction = all or nothing**

---

## Idempotency

The client sends:

```http
Idempotency-Key: abc-123
```

First request:

```text
abc-123
→ create Order #1
→ reduce stock
```

Retry with the same key:

```text
abc-123
→ return Order #1
→ do not reduce stock again
```

**Idempotency = retry does not repeat the operation**

---

## Transaction vs Idempotency

```text
Transaction
→ prevents partial operations

Idempotency
→ prevents duplicate operations
```

---

## Endpoint

```http
POST /orders
```

Example:

```json
{
  "product_id": 1,
  "quantity": 57
}
```

Header:

```http
Idempotency-Key: abc-123
```

The authenticated user comes from the JWT implemented in Episode 2.

---

## Tests

Episode 3 tests verify:

- Creating an order reduces stock
- Retrying with the same idempotency key returns the same order
- Inventory is not reduced twice
- Insufficient stock returns `409 Conflict`

Run:

```bash
./.venv/bin/python -m pytest -v
```

Expected:

```text
15 passed
```

---

## What Is Still Broken?

Inventory checking is not concurrency-safe yet.

```text
Stock = 1

Bob reads   → 1
Alice reads → 1
```

Both requests could try to buy the last banana.

That becomes:

## Episode 4: The Last Banana

Concurrency and database locking.
