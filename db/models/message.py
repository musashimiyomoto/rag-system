from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base
from enums import Role


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id"), index=True, comment="Session ID"
    )

    role: Mapped[Role] = mapped_column(comment="Role")
    content: Mapped[str] = mapped_column(comment="Content")
    thinking: Mapped[str | None] = mapped_column(comment="Thinking")
    timestamp: Mapped[datetime] = mapped_column(comment="Timestamp")
