from datetime import datetime

from pydantic import BaseModel, Field

from enums import Role


class MessageResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    session_id: int = Field(default=..., description="Session ID")

    role: Role = Field(default=..., description="Role")
    content: str = Field(default=..., description="Content")
    thinking: str | None = Field(default=None, description="Thinking")
    timestamp: datetime = Field(default=..., description="Timestamp")

    class Config:
        from_attributes = True
