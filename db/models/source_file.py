from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        unique=True,
        comment="Source ID",
    )
    content: Mapped[bytes] = mapped_column(LargeBinary, comment="Content")

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
