"""Add tool result fields to messages

Revision ID: 1a2b3c4d5e6f
Revises: b6c7d8e9f0a1
Create Date: 2026-03-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("web_search", sa.String(), nullable=True, comment="Web search"),
    )
    op.add_column(
        "messages",
        sa.Column("retrieve", sa.String(), nullable=True, comment="Retrieve"),
    )


def downgrade() -> None:
    op.drop_column("messages", "retrieve")
    op.drop_column("messages", "web_search")
