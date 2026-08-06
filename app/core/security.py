from pwdlib import PasswordHash

import jwt
from pwdlib import PasswordHash

from app.config import settings

from datetime import datetime, timedelta, timezone

# Create one reusable password-hashing object.
#
# PasswordHash.recommended() selects pwdlib's currently recommended
# password-hashing algorithm and configuration.
#
# We create this object once instead of rebuilding it every time
# a customer registers.
password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """
    Convert a plain-text password into a secure one-way hash.

    The plain password exists only while processing the request.
    We return the generated hash so that only the hash is stored
    in PostgreSQL.
    """

    return password_hash.hash(plain_password)

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Check whether the submitted password matches the hash stored
    in PostgreSQL.

    Used during login.
    """

    return password_hash.verify(
        plain_password,
        hashed_password,
    )

def create_access_token(subject: str) -> str:
    """
    Create a signed JWT access token.

    The subject is the identity represented by the token.
    For BananaKart, it will be the user's database ID.
    """

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    encoded_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_token