from datetime import datetime

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    source_id: int = Field(default=..., description="Source ID")


class SessionResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    source_id: int = Field(default=..., description="Source ID")

    created_at: datetime = Field(default=..., description="Created at")

    class Config:
        from_attributes = True
