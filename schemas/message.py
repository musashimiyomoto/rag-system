from datetime import datetime

from pydantic import BaseModel, Field

from enums import Role, ToolId


class MessageResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    session_id: int = Field(default=..., description="Session ID")

    role: Role = Field(default=..., description="Role")
    content: str = Field(default=..., description="Content")
    thinking: str | None = Field(default=None, description="Thinking")
    provider_id: int | None = Field(default=None, description="Provider ID")
    model_name: str | None = Field(default=None, description="Model name")
    tool_ids: list[ToolId] = Field(default_factory=list, description="Tool IDs")
    timestamp: datetime = Field(default=..., description="Timestamp")

    class Config:
        from_attributes = True
