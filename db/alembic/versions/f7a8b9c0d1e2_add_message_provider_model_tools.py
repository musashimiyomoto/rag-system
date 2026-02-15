"""Add provider_id, model_name, tool_ids to messages

Revision ID: f7a8b9c0d1e2
Revises: e1f2a3b4c5d6
Create Date: 2026-02-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("provider_id", sa.Integer(), nullable=True, comment="Provider ID"),
    )
    op.add_column(
        "messages",
        sa.Column("model_name", sa.String(), nullable=True, comment="Model name"),
    )
    op.add_column(
        "messages",
        sa.Column("tool_ids", sa.JSON(), nullable=True, comment="Tool IDs"),
    )
    op.execute("UPDATE messages SET tool_ids = '[]' WHERE tool_ids IS NULL")
    op.alter_column("messages", "tool_ids", nullable=False)


def downgrade() -> None:
    op.drop_column("messages", "tool_ids")
    op.drop_column("messages", "model_name")
    op.drop_column("messages", "provider_id")
