from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class SessionSource(Base):
    __tablename__ = "session_sources"
    __table_args__ = (UniqueConstraint("session_id", "source_id"),)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Session ID",
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
        comment="Source ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
