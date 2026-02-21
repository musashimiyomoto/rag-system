from pydantic import Field
from pydantic_settings import SettingsConfigDict

from settings.base import BaseSettings


class PrefectSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="prefect_")

    image: str = Field(
        default="prefecthq/prefect:3.4-python3.11", title="Prefect image"
    )
    host: str = Field(default="prefect-server", title="Prefect server host")
    port: int = Field(default=4200, title="Prefect server port")
    pool_name: str = Field(default="local-pool", title="Prefect pool name")

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


prefect_settings = PrefectSettings()
