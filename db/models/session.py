from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
