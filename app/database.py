from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# The engine manages database connections for the entire application.
# SQLAlchemy may reuse these connections through a connection pool.
engine = create_engine(
    settings.database_url,
    # Check whether a pooled connection is still alive before using it.
    # This helps avoid errors when PostgreSQL has closed an old connection.
    pool_pre_ping=True,
)

# SessionLocal is a factory.
# Calling SessionLocal() creates a new database session for one unit of work.
SessionLocal = sessionmaker(
    bind=engine,
    # Do not automatically send pending changes before every query.
    # We will control when changes are written.
    autoflush=False,
     # Keep loaded object values available after commit.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Future models such as User and Product will inherit from this class.
    SQLAlchemy uses it to track which Python classes represent database tables.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Provide one database session for each API request.

    FastAPI opens the session before the endpoint runs.
    The `finally` block closes it after the request finishes,
    even when an error occurs.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()