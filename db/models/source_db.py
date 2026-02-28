from datetime import datetime

from sqlalchemy import JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base
from enums import SourceType


class SourceDb(Base):
    __tablename__ = "source_dbs"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        unique=True,
        comment="Source ID",
    )
    db_type: Mapped[SourceType] = mapped_column(comment="DB type")
    connection_encrypted: Mapped[str] = mapped_column(comment="Encrypted connection")
    schema_name: Mapped[str] = mapped_column(comment="Schema name")
    table_name: Mapped[str] = mapped_column(comment="Table name")
    id_field: Mapped[str] = mapped_column(comment="ID field")
    search_field: Mapped[str] = mapped_column(comment="Search field")
    filter_fields: Mapped[list[str]] = mapped_column(JSON, comment="Filter fields")

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), comment="Updated at"
    )
