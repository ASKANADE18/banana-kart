from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import settings
from app.database import Base

# Import every model that Alembic needs to discover.
# Without this import, Base.metadata would not know that User exists.
from app.models.user import User  # noqa: F401


# Alembic gives us this configuration object.
config = context.config


# Configure logging using the settings inside alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Alembic compares this metadata against the actual PostgreSQL schema.
# Every model inheriting from Base contributes table information here.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Generate SQL without opening a live database connection.

    We will normally use online migrations, but Alembic expects
    both offline and online modes to be configured.
    """

    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Connect to PostgreSQL and apply migrations directly.
    """

    # Alembic only needs a temporary connection.
    # NullPool prevents it from maintaining an application-style pool.
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,

            # Detect changes such as String(100) becoming String(255).
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Alembic decides which migration mode is being requested.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()