from pydantic import BaseModel, Field

from enums import ToolId


class ToolResponse(BaseModel):
    id: ToolId = Field(default=..., description="Tool ID")
    title: str = Field(default=..., description="Tool title")
    description: str = Field(default=..., description="Tool description")
    enabled_by_default: bool = Field(default=..., description="Enabled by default")
    requires_sources: bool = Field(
        default=..., description="Whether tool requires sources"
    )
