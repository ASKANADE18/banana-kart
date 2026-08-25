from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password

from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse

from fastapi import Request

# from app.rate_limit import check_fixed_window_rate_limit
# from app.rate_limit import check_sliding_window_rate_limit
from app.rate_limit import check_token_bucket_rate_limit

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
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    
    client_ip = request.client.host

    rate_limit_key = f"rate_limit:login:{client_ip}"

    # allowed = check_fixed_window_rate_limit(
    #     key=rate_limit_key,
    #     limit=5,
    #     window_seconds=60,
    # )

    # allowed = check_sliding_window_rate_limit(
    #     key=f"rate_limit:sliding:login:{client_ip}",
    #     limit=5,
    #     window_seconds=60,
    # )
    allowed = check_token_bucket_rate_limit(
        key=f"rate_limit:token:login:{client_ip}",
        capacity=5,
        refill_interval_seconds=10,
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
        )

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
