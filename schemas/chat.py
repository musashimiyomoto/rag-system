from datetime import datetime

from pydantic import BaseModel, Field

from constants import UTF8
from enums import Role, ToolId


class ChatRequest(BaseModel):
    message: str = Field(default=..., description="The message to chat")
    session_id: int = Field(default=..., description="The session ID")


class ChatResponse(BaseModel):
    role: Role = Field(default=..., description="The role of the message")
    timestamp: datetime = Field(default=..., description="The timestamp of the message")
    content: str = Field(default=..., description="The content of the message")
    provider_id: int | None = Field(default=None, description="The provider ID")
    model_name: str | None = Field(default=None, description="The model name")
    tool_ids: list[ToolId] = Field(default_factory=list, description="The tool IDs")

    def model_dump_bytes(self) -> bytes:
        """Dump the model to bytes.

        Returns:
            The bytes of the model.

        """
        return self.model_dump_json().encode(UTF8) + b"\n"
