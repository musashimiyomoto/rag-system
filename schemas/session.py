from datetime import datetime

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    source_ids: list[int] = Field(default_factory=list, description="Source IDs")


class SessionResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    source_ids: list[int] = Field(default_factory=list, description="Source IDs")

    created_at: datetime = Field(default=..., description="Created at")

    class Config:
        from_attributes = True
