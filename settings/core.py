from pydantic import Field
from pydantic_settings import SettingsConfigDict

from .base import BaseSettings


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="core_")

    max_file_size: int = Field(default=1024 * 1024 * 10, title="Max file size")
    google_api_key: str = Field(default="", title="Google API key")
    github_api_key: str = Field(default="", title="GitHub API key")
    openai_api_key: str = Field(default="", title="OpenAI API key")


core_settings = CoreSettings()
