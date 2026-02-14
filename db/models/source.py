from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base
from enums import SourceStatus, SourceType


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    name: Mapped[str] = mapped_column(comment="Name")
    type: Mapped[SourceType] = mapped_column(comment="Type")
    status: Mapped[SourceStatus] = mapped_column(comment="Status")
    collection: Mapped[str] = mapped_column(comment="Collection")
    summary: Mapped[str | None] = mapped_column(comment="Summary")

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), comment="Updated at"
    )
