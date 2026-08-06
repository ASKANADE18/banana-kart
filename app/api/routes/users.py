from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

from typing import Annotated
from app.api.dependencies.auth import get_current_user


# A router groups endpoints that belong to the same resource.
#
# Because the prefix is "/users", every endpoint in this file
# will begin with /users.
router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get(
    "/me",
    response_model=UserResponse,
)
def read_current_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """
    Return the profile of the authenticated user.

    The endpoint does not accept a user ID from the client.
    The identity comes from the verified JWT.
    """

    return current_user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    # FastAPI reads the request JSON and validates it using UserCreate.
    user_data: UserCreate,

    # FastAPI calls get_db() and gives this request a database session.
    db: Session = Depends(get_db),
) -> User:
    """
    Register a new BananaKart customer.

    Request flow:
    1. Validate the incoming JSON.
    2. Normalize the email.
    3. Check whether the email is already registered.
    4. Hash the password.
    5. Insert the user into PostgreSQL.
    6. Return only safe user fields.
    """

    # Convert the email to lowercase so these are treated as the same:
    #
    # Ashwini@Example.com
    # ashwini@example.com
    normalized_email = str(user_data.email).lower()

    # Ask PostgreSQL whether a user already has this email.
    statement = select(User).where(
        User.email == normalized_email
    )

    existing_user = db.scalar(statement)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    # Convert the validated API request into a SQLAlchemy model.
    #
    # Notice:
    # user_data.password is received from the client.
    # hashed_password is what we store in the database.
    new_user = User(
        name=user_data.name,
        email=normalized_email,
        phone_number=user_data.phone_number,
        hashed_password=hash_password(user_data.password),
    )

    # Add the new object to the current database session.
    #
    # This prepares the INSERT, but it is not permanently saved yet.
    db.add(new_user)

    try:
        # Commit permanently saves the new user in PostgreSQL.
        db.commit()

    except IntegrityError:
        # Suppose two signup requests with the same email arrive together.
        #
        # Both could pass our first duplicate-email check, but the database's
        # unique email index will reject one of the INSERT operations.
        #
        # After a failed transaction, we must rollback before using
        # this database session again.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    # PostgreSQL generated fields such as:
    #
    # id
    # created_at
    # updated_at
    #
    # refresh() reloads those values into the new_user object.
    db.refresh(new_user)

    # FastAPI converts this SQLAlchemy object into UserResponse.
    # Fields not present in UserResponse, including hashed_password,
    # will not be returned to the client.
    return new_user
