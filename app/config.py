from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Stores application configuration.

    Pydantic reads these values from environment variables or the .env file.
    This keeps passwords and other configuration out of our Python source code.
    """

    postgres_user: str
    postgres_password: str
    postgres_db: str
    # These defaults are suitable for local development.
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Tell Pydantic where to find our local environment variables.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def database_url(self) -> str:
        """
        Build the connection URL that SQLAlchemy uses to connect to PostgreSQL.

        `postgresql+psycopg` means:
        - PostgreSQL is our database
        - psycopg is the Python database driver
        """

        return (
            f"postgresql+psycopg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )


# Create one settings object that the rest of the application can import.
settings = Settings()