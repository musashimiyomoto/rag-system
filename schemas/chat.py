from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from constants import UTF8
from enums import Role, ToolId


class RetrieveToolRequest(BaseModel):
    id: Literal[ToolId.RETRIEVE] = Field(
        default=ToolId.RETRIEVE, description="Retrieve tool ID"
    )
    source_ids: list[int] = Field(
        default=..., min_length=1, description="Source IDs to use for retrieve tool"
    )


class WebSearchToolRequest(BaseModel):
    id: Literal[ToolId.WEB_SEARCH] = Field(
        default=ToolId.WEB_SEARCH, description="Web search tool ID"
    )


class DeepThinkToolRequest(BaseModel):
    id: Literal[ToolId.DEEP_THINK] = Field(
        default=ToolId.DEEP_THINK, description="Deep think tool ID"
    )


ChatToolRequest = Annotated[
    RetrieveToolRequest | WebSearchToolRequest | DeepThinkToolRequest,
    Field(discriminator="id"),
]


class ChatRequest(BaseModel):
    message: str = Field(default=..., description="The message to chat")
    session_id: int = Field(default=..., description="The session ID")
    provider_id: int = Field(default=..., gt=0, description="The provider ID")
    model_name: str = Field(default=..., min_length=1, description="The model name")
    tools: list[ChatToolRequest] = Field(
        default_factory=list, description="Tools configuration for this request"
    )

    @model_validator(mode="after")
    def validate_unique_tools(self) -> "ChatRequest":
        tool_ids = [tool.id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            msg = "Duplicate tool IDs are not allowed"
            raise ValueError(msg)
        return self


class ChatResponse(BaseModel):
    role: Role = Field(default=..., description="The role of the message")
    timestamp: datetime = Field(default=..., description="The timestamp of the message")
    content: str = Field(default=..., description="The content of the message")
    thinking: str | None = Field(default=None, description="The thinking content")
    provider_id: int | None = Field(default=None, description="The provider ID")
    model_name: str | None = Field(default=None, description="The model name")
    tool_ids: list[ToolId] = Field(default_factory=list, description="The tool IDs")

    def model_dump_bytes(self) -> bytes:
        return self.model_dump_json().encode(UTF8) + b"\n"
