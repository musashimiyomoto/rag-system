from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from enums import ProviderName


class ProviderBaseRequest(BaseModel):
    name: ProviderName = Field(default=..., description="Provider name")


class ProviderCreateRequest(ProviderBaseRequest):
    api_key: str | None = Field(default=None, description="Provider API key")

    @model_validator(mode="after")
    def validate_api_key(self) -> "ProviderCreateRequest":
        if self.name in (ProviderName.OPENAI, ProviderName.GOOGLE) and (
            not self.api_key or not self.api_key.strip()
        ):
            msg = f"api_key is required for provider: {self.name}"
            raise ValueError(msg)

        return self


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
