from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and return a JWT access token.

    OAuth2 calls the first form field `username`.
    BananaKart treats that field as the user's email address.
    """

    # Normalize the email exactly as we did during registration.
    email = form_data.username.strip().lower()

    # Search PostgreSQL for a user with this email.
    user = db.scalar(
        select(User).where(User.email == email)
    )

    # Return the same public error for both cases:
    # 1. The email does not exist.
    # 2. The password is incorrect.
    #
    # This prevents attackers from discovering registered emails.
    if user is None or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Store only the user's ID in the token subject.
    access_token = create_access_token(
        subject=str(user.id)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )
