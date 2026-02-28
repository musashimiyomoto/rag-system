from pydantic import Field
from pydantic_settings import SettingsConfigDict

from settings.base import BaseSettings


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="postgres_")

    image: str = Field(default="postgres:14", title="Postgres image")
    host: str = Field(default="postgres", title="Postgres host")
    port: int = Field(default=5432, title="Postgres port")
    user: str = Field(default="postgres", title="Postgres user")
    password: str = Field(default="postgres", title="Postgres password")
    db: str = Field(default="postgres", title="Postgres db")

    @property
    def url(self) -> str:
        """Url.

        Returns:
            Postgres SQLAlchemy DSN.

        """
        return (
            f"postgresql+asyncpg://"
            f"{self.user}:"
            f"{self.password}@"
            f"{self.host}:"
            f"{self.port}/"
            f"{self.db}"
        )


postgres_settings = PostgresSettings()
