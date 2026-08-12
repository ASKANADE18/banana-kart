# BananaKart Backend Chronicles

## Episode 4: The Last Banana

There is only one banana left.

Bob and Alice both try to buy it at the same time.

Without concurrency control, both requests could read:

```text
stock = 1
```

and both think the purchase is valid.

## Problem: Race Condition

```text
Bob reads stock = 1
Alice reads stock = 1

Bob buys ✅
Alice buys ✅

But only one banana existed.
```

## Solution: Row Locking

The product is selected using:

```sql
SELECT *
FROM products
WHERE id = ?
FOR UPDATE;
```

In SQLAlchemy:

```python
select(Product)
.where(Product.id == product_id)
.with_for_update()
```

PostgreSQL locks that product row until the transaction ends.

```text
Bob locks row
   ↓
Alice waits
   ↓
Bob updates stock and commits
   ↓
lock released
   ↓
Alice sees latest stock
   ↓
409 Not Enough Stock
```

## Transaction vs Lock

```text
Transaction
→ all or nothing

Row lock
→ competing transactions wait their turn
```

## Tests

The concurrency test sends two purchase requests at roughly the same time.

Expected result:

```text
one request → 201 Created
one request → 409 Conflict
final stock → 0
```

Run:

```bash
./.venv/bin/python -m pytest -v
```

Expected:

```text
16 passed
```

## Next Episode

Episode 5: Database Starts Crying

Indexes, query performance, and pagination.
