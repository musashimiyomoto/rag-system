from datetime import datetime

from pydantic import BaseModel, Field

from enums import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    name: str = Field(default=..., description="Name")
    type: DocumentType = Field(default=..., description="Type")
    status: DocumentStatus = Field(default=..., description="Status")
    collection: str = Field(default=..., description="Collection")
    summary: str | None = Field(default=None, description="Summary")

    created_at: datetime = Field(default=..., description="Created at")
    updated_at: datetime = Field(default=..., description="Updated at")

    class Config:
        from_attributes = True
