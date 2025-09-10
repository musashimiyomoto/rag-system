from datetime import datetime

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    document_id: int = Field(default=..., description="Document ID")


class SessionResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    document_id: int = Field(default=..., description="Document ID")

    created_at: datetime = Field(default=..., description="Created at")

    class Config:
        from_attributes = True
