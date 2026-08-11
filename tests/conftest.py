from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Import all SQLAlchemy models so they are registered with Base.metadata
# before create_all() creates the test tables.
from app.models.user import User  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.order import Order  # noqa: F401


# ---------------------------------------------------------
# TEST DATABASE SETUP
# ---------------------------------------------------------

# This engine connects only to the test database.
# It must never point to the normal BananaKart development database.
test_engine = create_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)


# Create database sessions that use the test database.
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------
# API CLIENT FIXTURE
# ---------------------------------------------------------

@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """
    Provide an isolated API client for each test.

    Before the test:
    - Recreate the test tables.
    - Replace BananaKart's normal database dependency.

    After the test:
    - Remove the dependency override.
    - Delete the test tables.
    """

    # Start every test with an empty test database.
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        """
        Give API requests a test database session instead of
        the normal BananaKart database session.
        """

        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    # Whenever an endpoint asks for get_db(),
    # FastAPI will use the test database instead.
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Remove test-specific dependency overrides.
    app.dependency_overrides.clear()

    # Remove all test data after the test.
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------
# DIRECT DATABASE FIXTURE
# ---------------------------------------------------------

@pytest.fixture()
def db_session(
    client: TestClient,
) -> Generator[Session, None, None]:
    """
    Give test code direct access to the same test database.

    Depending on `client` ensures:
    - test tables have already been created
    - FastAPI is also using the test database
    """

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()