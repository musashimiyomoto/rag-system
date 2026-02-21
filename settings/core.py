from pydantic import Field
from pydantic_settings import SettingsConfigDict

from settings.base import BaseSettings


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="core_")

    max_file_size: int = Field(default=1024 * 1024 * 10, title="Max file size")
    master_key: str = Field(default="change-me-master-key", title="Master key")
    sources_index_collection: str = Field(
        default="sources_index",
        title="Vector DB collection name for source indexing",
    )


core_settings = CoreSettings()
