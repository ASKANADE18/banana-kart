# BananaKart Backend Chronicles

## Episode 8: The Email Intern Quit

Order creation should not wait for slow, non-critical work such as sending confirmation emails.

This episode introduces background processing and explains when simple in-process background work is enough and when a durable queue-based system is needed.

---

## Problem

The original request flow looked like this:

```text
POST /orders
↓
create order
↓
send confirmation email
↓
return response
```

This creates two problems:

```text
1. The user waits for the email work to finish.
2. Email failure can affect the main order request.
```

The order is critical business work.

The email is a non-critical side effect.

So the flow should be separated.

---

## Implemented

- FastAPI `BackgroundTasks`
- Order confirmation email simulation
- Background task scheduled only after successful database commit
- Automated test using a mocked email function

---

## Order Flow

```text
POST /orders
↓
authenticate user
↓
validate request
↓
check idempotency key
↓
load product
↓
check stock
↓
create order
↓
decrease stock
↓
db.commit()
↓
clear Redis cache
↓
schedule confirmation email
↓
return 201 Created
↓
background email task runs
```

The important idea is:

```text
Critical work
→ complete before response

Non-critical work
→ run after response
```

---

## Email Helper

The current email implementation is intentionally simple.

```python
def send_order_confirmation_email(
    email: str,
    order_id: int,
) -> None:
    print(
        f"Sending order confirmation email to {email} "
        f"for order {order_id}"
    )
```

This simulates sending an email.

A real email provider such as AWS SES could later replace the `print()` without changing the overall background-task flow.

---

## FastAPI BackgroundTasks

The order route receives:

```python
background_tasks: BackgroundTasks
```

After the order is successfully committed:

```python
db.commit()
db.refresh(order)

background_tasks.add_task(
    send_order_confirmation_email,
    current_user.email,
    order.id,
)
```

The HTTP response can be completed without waiting for the email logic.

---

## Why Commit Before Scheduling the Email?

This order is safer:

```text
db.commit()
↓
order definitely exists
↓
schedule email
```

This would be risky:

```text
schedule email
↓
db.commit()
```

If the email is triggered first but the database commit later fails, the customer could receive a confirmation email for an order that does not exist.

Rule:

```text
Persist critical state first
→ then trigger side effects
```

---

## BackgroundTasks Limitation

`BackgroundTasks` is useful for small, simple background work.

However, it runs in the same application process.

Example failure:

```text
FastAPI returns 201
↓
background email task starts
↓
server crashes
↓
task may be lost
```

So `BackgroundTasks` is **not a durable job queue**.

---

## When a Queue Is Better

For important work that needs retries or must survive application crashes, a durable queue such as Amazon SQS is more appropriate.

Conceptual flow:

```text
FastAPI
↓
SQS
↓
worker
↓
email provider
```

A queue can provide:

```text
durable message storage
retries
multiple workers
independent scaling
failure isolation
```

---

## Database Commit and Queue Failure

Even with SQS, there is another possible failure:

```text
db.commit()
↓
order saved
↓
application crashes
↓
SQS message never sent
```

The order exists, but the email event is lost.

A normal PostgreSQL transaction cannot automatically include SQS because they are separate systems.

```text
PostgreSQL
≠
SQS
```

---

## Transactional Outbox Pattern

A common solution is the **Transactional Outbox Pattern**.

Instead of immediately sending the event to SQS:

```text
BEGIN
↓
insert order
↓
insert outbox event
↓
COMMIT
```

For example, the database could contain:

```text
orders
outbox_events
```

The order and event are stored in the same PostgreSQL transaction.

Therefore:

```text
order saved + event saved
```

or:

```text
neither saved
```

A separate worker later reads pending outbox events and publishes them to SQS.

---

## Outbox Worker Flow

```text
outbox_events
↓
worker reads pending event
↓
send event to SQS
↓
success
↓
mark event processed
```

Processed events can be kept temporarily for:

```text
debugging
audit/history
failure investigation
```

Old processed events can later be cleaned up.

---

## Duplicate Processing

A distributed system can retry work.

Example:

```text
worker sends event to SQS
↓
worker crashes before marking event processed
↓
worker retries
↓
same event may be sent again
```

Similarly:

```text
consumer receives message
↓
sends email
↓
crashes before recording completion
↓
message is delivered again
↓
email could be sent twice
```

This is why consumers should be **idempotent**.

---

## Idempotent Consumer

Every event can have a unique identifier:

```text
event_id
```

The consumer checks whether that event has already been processed.

```text
receive event_id
↓
already processed?

yes
→ skip

no
→ process
→ record event_id
```

This makes retries safe.

---

## Delivery Semantics

### At-Most-Once

```text
processed 0 or 1 time
```

Duplicates are avoided, but the message may be lost.

### At-Least-Once

```text
processed 1 or more times
```

Retries are possible, but duplicate processing can happen.

### Exactly-Once

```text
processed exactly 1 time
```

This is difficult to guarantee across multiple distributed systems.

A common practical approach is:

```text
at-least-once delivery
+
idempotent consumer
=
safe retries
```

---

## Dead-Letter Queue

A message should not retry forever.

Example:

```text
message
↓
processing fails
↓
retry
↓
fails
↓
retry
↓
fails again
↓
DLQ
```

A **Dead-Letter Queue (DLQ)** stores messages that repeatedly fail.

This allows bad messages to be inspected separately without blocking normal processing.

---

## Automated Testing

The background email task is tested without using a real email provider.

The test keeps the real application flow but mocks the external email function.

```text
TestClient
↓
real POST /orders route
↓
real database operations
↓
mocked email function
↓
verify function was called
```

Testing principle:

```text
Mock the external side effect
not the entire application
```

---

## Manual Verification

A real order request returned:

```text
201 Created
```

The application terminal showed:

```text
Sending order confirmation email to ashwini@example.com for order 4
```

This verified that the order completed successfully and the email function ran as background work.

---

## What Was Actually Implemented

```text
FastAPI BackgroundTasks
order confirmation task
email simulation with print()
background task after DB commit
automated background-task test
```

---

## What Was Learned Conceptually

```text
SQS
durable queues
retryable workers
Transactional Outbox Pattern
idempotent consumers
at-most-once delivery
at-least-once delivery
exactly-once processing
Dead-Letter Queue
```

---

## What Was Not Implemented

The current project does not include:

```text
real email provider
real SQS queue
worker service
outbox_events database table
DLQ configuration
automatic retry framework
```

These were intentionally learned as architecture concepts rather than added to the codebase.

---

## Key Takeaways

```text
BackgroundTasks
→ simple same-process work after response

SQS
→ durable + retryable + scalable queue

Transactional Outbox
→ prevents losing events between DB commit and queue publish

Idempotent Consumer
→ makes duplicate delivery safe

DLQ
→ isolates repeatedly failing messages
```

---

## Fast Memory

```text
Critical work
→ commit first

Non-critical work
→ background

Simple task
→ BackgroundTasks

Durable important task
→ Queue

DB + event consistency
→ Transactional Outbox

Duplicate messages
→ Idempotent Consumer

Repeated failure
→ DLQ
```
