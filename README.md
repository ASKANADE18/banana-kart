# BananaKart Backend Chronicles

## Episode 2: Everyone Is Anonymous

BananaKart could register users, but every later request was anonymous.

The CEO suggested trusting a `user_id` sent by the client.

That idea was rejected immediately.

This episode adds JWT-based authentication so the backend can verify who is making each request.

---

## Implemented

- Password verification with Argon2
- OAuth2 login form
- JWT access tokens
- Token expiration
- Bearer-token authentication
- Reusable current-user dependency
- Protected `/users/me` endpoint
- Generic login errors
- Authentication tests

---

## Authentication Flow

```text
Email + password
      ↓
Verify password against stored hash
      ↓
Create signed JWT
      ↓
Client sends JWT in Authorization header
      ↓
Backend verifies JWT and loads the user
```

---

## Endpoints

### Register

```http
POST /users
```

Example request:

```json
{
  "name": "Ashwini Kanade",
  "email": "ashwini@example.com",
  "phone_number": "8625880595",
  "password": "banana-secret-123"
}
```

### Login

```http
POST /auth/login
```

Login uses form data:

```text
username=ashwini@example.com
password=banana-secret-123
```

Successful response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Current User

```http
GET /users/me
```

Required header:

```http
Authorization: Bearer <access-token>
```

The endpoint gets the user ID from the verified token instead of accepting it from the client.

---

## JWT Payload

Example:

```json
{
  "sub": "5",
  "exp": 1785980000
}
```

```text
sub → authenticated user ID
exp → token expiration time
```

JWTs are signed, not encrypted. Passwords, password hashes, and other secrets must never be placed inside them.

---

## Authentication Errors

BananaKart returns:

```http
401 Unauthorized
```

for:

- Incorrect email or password
- Missing token
- Invalid token
- Expired token
- Missing `sub` claim
- Nonexistent user

Incorrect email and incorrect password return the same message:

```json
{
  "detail": "Invalid email or password"
}
```

This prevents attackers from discovering registered email addresses.

---

## Environment Variables

```env
JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Real secrets belong in `.env`.

Safe placeholders belong in `.env.example`.

---

## Project Structure

```text
app/
├── api/
│   ├── dependencies/
│   │   └── auth.py
│   └── routes/
│       ├── auth.py
│       └── users.py
├── core/
│   └── security.py
├── schemas/
│   ├── auth.py
│   └── user.py
├── config.py
├── database.py
└── main.py

tests/
├── conftest.py
├── test_auth.py
└── test_users.py
```

---

## File Responsibilities

```text
app/api/routes/auth.py
→ Handles the login endpoint.

app/api/dependencies/auth.py
→ Validates JWTs and loads the current authenticated user.

app/core/security.py
→ Hashes passwords, verifies passwords, and creates JWTs.

app/schemas/auth.py
→ Defines the login token response.

app/api/routes/users.py
→ Handles registration and the protected profile endpoint.

tests/test_auth.py
→ Verifies successful authentication and authentication failures.
```

---

## Run the Project

Start PostgreSQL:

```bash
docker compose up -d
```

Start FastAPI:

```bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## Run Tests

```bash
./.venv/bin/python -m pytest -v
```

Expected:

```text
12 passed
```

---

## Episode Outcome

Before:

```text
Every request was anonymous.
```

After:

```text
BananaKart can verify the current user.
```

The customers now have identities.

Their suspicious banana purchases are Episode 3’s problem.
