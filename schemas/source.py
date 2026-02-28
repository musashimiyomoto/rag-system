from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from enums import SourceStatus, SourceType


class SourceResponse(BaseModel):
    id: int = Field(default=..., description="ID", gt=0)

    name: str = Field(default=..., description="Name")
    type: SourceType = Field(default=..., description="Type")
    status: SourceStatus = Field(default=..., description="Status")
    collection: str = Field(default=..., description="Collection")
    summary: str | None = Field(default=None, description="Summary")

    created_at: datetime = Field(default=..., description="Created at")
    updated_at: datetime = Field(default=..., description="Updated at")

    class Config:
        from_attributes = True


class DbCredentialsPostgres(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default=..., min_length=1)
    port: int = Field(default=5432, gt=0)
    database: str = Field(default=..., min_length=1)
    user: str = Field(default=..., min_length=1)
    password: str = Field(default=..., min_length=1)
    sslmode: str | None = Field(default=None)


class DbCredentialsClickHouse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default=..., min_length=1)
    port: int = Field(default=8123, gt=0)
    database: str = Field(default=..., min_length=1)
    user: str = Field(default=..., min_length=1)
    password: str = Field(default=..., min_length=1)
    secure: bool = Field(default=False)


DbCredentials = Annotated[DbCredentialsPostgres | DbCredentialsClickHouse, Field()]


class DbSourceIntrospectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: SourceType = Field(default=...)
    credentials: DbCredentials = Field(default=...)
    schema_name: str | None = Field(
        default=None,
        validation_alias="schema",
        serialization_alias="schema",
    )


class DbColumnSchema(BaseModel):
    name: str = Field(default=...)
    type: str = Field(default=...)
    nullable: bool = Field(default=...)


class DbTableSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: str = Field(
        default=...,
        validation_alias="schema",
        serialization_alias="schema",
    )
    table: str = Field(default=...)
    columns: list[DbColumnSchema] = Field(default_factory=list)


class DbSourceIntrospectResponse(BaseModel):
    tables: list[DbTableSchema] = Field(default_factory=list)


class DbSourceCreateRequest(BaseModel):
    name: str | None = Field(default=None)
    type: SourceType = Field(default=...)
    credentials: DbCredentials = Field(default=...)
    schema_name: str = Field(default=..., min_length=1)
    table_name: str = Field(default=..., min_length=1)
    id_field: str = Field(default=..., min_length=1)
    search_field: str = Field(default=..., min_length=1)
    filter_fields: list[str] = Field(default_factory=list)
