## Episode 1: The CEO Wants Users

### Incident

BananaKart had no user system. Customers could not register, and the CEO’s proposed backup plan was a shared spreadsheet containing names, emails, and passwords.

That plan was rejected for several reasons, including common sense.

### Implemented

- PostgreSQL running through Docker
- Persistent database storage using Docker volumes
- Environment-based configuration using `.env`
- SQLAlchemy engine and database sessions
- `users` database table
- Alembic migration history
- Pydantic request and response schemas
- Argon2 password hashing
- User registration endpoint
- Duplicate-email protection
- Input validation
- Separate test database
- Automated API tests

### User Table

```text
users
├── id
├── name
├── email
├── phone_number
├── hashed_password
├── created_at
└── updated_at
```

The email column uses a unique index to prevent duplicate accounts and improve email lookups.

### Registration Endpoint

```http
POST /users
```

Example request:

```json
{
  "name": "Ashwini Kanade",
  "email": "ashwini@example.com",
  "phone_number": "+1-201-555-0123",
  "password": "banana-secret-123"
}
```

Example response:

```json
{
  "id": 1,
  "name": "Ashwini Kanade",
  "email": "ashwini@example.com",
  "phone_number": "+1-201-555-0123",
  "created_at": "2026-08-04T20:00:00Z",
  "updated_at": "2026-08-04T20:00:00Z"
}
```

Plain-text passwords are never stored or returned. Only the generated Argon2 hash is saved in PostgreSQL.

### Registration Flow

```text
Client
  ↓
POST /users
  ↓
Pydantic validation
  ↓
Duplicate-email check
  ↓
Password hashing
  ↓
SQLAlchemy transaction
  ↓
PostgreSQL
  ↓
Safe response
```

### Error Responses

Duplicate email:

```http
409 Conflict
```

Invalid request data:

```http
422 Unprocessable Entity
```

### Automated Tests

The Episode 1 test suite verifies:

- Successful registration
- Duplicate-email rejection
- Invalid-request validation
- Password fields are not exposed

```markdown
Episode 1 adds three automated tests covering these behaviors.

---

# Running Locally

## 1. Create the virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Create `.env`

```env
POSTGRES_USER=bananakart_user
POSTGRES_PASSWORD=your_local_password
POSTGRES_DB=bananakart
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

TEST_DATABASE_URL=postgresql+psycopg://bananakart_user:your_local_password@localhost:5432/bananakart_test
```

Do not commit `.env`.

## 4. Start PostgreSQL

```bash
docker compose up -d
```

## 5. Apply migrations

```bash
./.venv/bin/alembic upgrade head
```

## 6. Start the API

```bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Running Tests

The tests use a separate PostgreSQL database named `bananakart_test`.

Create it once after starting PostgreSQL:

```bash
docker exec -it bananakart-postgres \
createdb -U bananakart_user \
-O bananakart_user \
bananakart_test
```

If the database already exists, this step can be skipped.

Run the tests:

```bash
./.venv/bin/python -m pytest -v
```