from pydantic import BaseModel, Field

from enums import ToolId


class ToolResponse(BaseModel):
    id: ToolId = Field(default=..., description="Tool ID")
    title: str = Field(default=..., description="Tool title")
    description: str = Field(default=..., description="Tool description")
