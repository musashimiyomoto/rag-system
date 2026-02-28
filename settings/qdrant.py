from uuid import UUID

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from settings.base import BaseSettings


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="qdrant_")

    image: str = Field(default="qdrant/qdrant:v1.13.4", title="Qdrant image")
    host: str = Field(default="qdrant", title="Qdrant host")
    port: int = Field(default=6333, title="Qdrant port")
    vector_size: int = Field(default=384, title="Embedding vector size")
    distance: str = Field(default="Cosine", title="Distance metric")
    point_id_namespace: UUID = Field(
        default=UUID("d8a0d157-c9dd-4af8-ad5e-4b3a6a4d1f15"),
        title="Namespace for deterministic point ID UUIDv5 mapping",
    )

    @property
    def url(self) -> str:
        """Url.

        Returns:
            Qdrant base URL.

        """
        return f"http://{self.host}:{self.port}"


qdrant_settings = QdrantSettings()
