from datetime import datetime

from pydantic import BaseModel, Field

from enums import ProviderName


class ProviderBaseRequest(BaseModel):
    name: ProviderName = Field(default=..., description="Provider name")


class ProviderCreateRequest(ProviderBaseRequest):
    api_key: str = Field(default=..., description="Provider API key", min_length=1)


class ProviderUpdateRequest(BaseModel):
    api_key: str | None = Field(default=None, description="Provider API key")
    is_active: bool | None = Field(default=None, description="Is active")


class ProviderResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)
    name: ProviderName = Field(default=..., description="Provider name")
    is_active: bool = Field(default=..., description="Is active")
    api_key_encrypted: str = Field(default=..., description="Masked API key")
    created_at: datetime = Field(default=..., description="Created at")
    updated_at: datetime = Field(default=..., description="Updated at")

    class Config:
        from_attributes = True


class ProviderModelResponse(BaseModel):
    name: str = Field(default=..., description="Model name")
