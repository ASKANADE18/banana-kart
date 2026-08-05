from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """
    Defines the JSON body accepted by POST /users.

    This is not a database table. It controls what a customer
    is allowed to send when creating an account.
    """

    # Remove accidental spaces from the beginning and end of strings.
    # Example: " Ashwini " becomes "Ashwini".
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Ashwini Kanade"],
    )

    # EmailStr checks that the value resembles a valid email address.
    email: EmailStr = Field(
        examples=["ashwini@example.com"],
    )

    # Phone number is optional because customers may register without one.
    phone_number: str | None = Field(
        default=None,
        max_length=20,
        examples=["+1-201-555-0123"],
    )

    # The customer sends a normal password.
    # We will hash it before creating the SQLAlchemy User object.
    password: str = Field(
        min_length=8,
        max_length=128,
        examples=["banana-secret-123"],
    )


class UserResponse(BaseModel):
    """
    Defines the safe JSON returned after creating a user.

    Password and hashed_password are deliberately excluded.
    """

    id: int
    name: str
    email: EmailStr
    phone_number: str | None
    created_at: datetime
    updated_at: datetime

    # Allows Pydantic to read values from a SQLAlchemy User object.
    model_config = ConfigDict(
        from_attributes=True,
    )