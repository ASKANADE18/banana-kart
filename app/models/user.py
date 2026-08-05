from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    Represents one customer account in BananaKart.

    SQLAlchemy maps this Python class to the PostgreSQL `users` table.
    Each object created from this class represents one row in that table.
    """

    # The name of the table that PostgreSQL will create.
    __tablename__ = "users"

    # Primary keys uniquely identify rows.
    # PostgreSQL automatically generates increasing integer values.
    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # A name is required, but it does not need to be unique.
    # Many customers can have the same name.
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Email is required and must be unique.
    # The index helps PostgreSQL find a user by email efficiently.
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Phone numbers are optional and do not need to be unique.
    # We use String instead of Integer because phone numbers can contain
    # country codes, leading zeroes, spaces, and symbols such as +.
    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # We never store a plain-text password.
    # Authentication will later create and verify password hashes.
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # PostgreSQL sets this timestamp when the row is first created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # PostgreSQL sets the initial value.
    # SQLAlchemy updates it when this model is modified.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )