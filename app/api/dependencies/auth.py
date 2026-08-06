from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User


# This tells FastAPI:
# - Protected endpoints expect a Bearer token.
# - Clients can obtain that token from POST /auth/login.
#
# The value is relative to the application root.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login"
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Validate the access token and return the user it represents.

    This dependency runs before every endpoint that requires
    an authenticated user.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode verifies:
        # 1. The token signature
        # 2. The token expiration time
        #
        # We explicitly provide the allowed algorithm instead of
        # trusting the algorithm written inside the token.
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # The subject contains the user's database ID.
        subject = payload.get("sub")

        if subject is None:
            raise credentials_exception

        user_id = int(subject)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        # Invalid signature, expired token, malformed token,
        # missing/invalid user ID, etc.
        raise credentials_exception

    # Confirm that the user still exists.
    user = db.get(User, user_id)

    if user is None:
        raise credentials_exception

    return user
