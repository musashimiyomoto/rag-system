from pydantic import Field
from pydantic_settings import SettingsConfigDict

from settings.base import BaseSettings


class SentrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="sentry_")

    dsn: str | None = Field(default=None, title="Sentry DSN")


sentry_settings = SentrySettings()
