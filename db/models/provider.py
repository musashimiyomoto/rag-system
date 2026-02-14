from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base
from enums import ProviderName


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, unique=True, comment="ID"
    )

    name: Mapped[ProviderName] = mapped_column(comment="Name")
    api_key_encrypted: Mapped[str] = mapped_column(comment="Encrypted API key")
    is_active: Mapped[bool] = mapped_column(default=True, comment="Is active")

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Created at"
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), comment="Updated at"
    )
