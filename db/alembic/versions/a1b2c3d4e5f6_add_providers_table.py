"""Add providers table

Revision ID: a1b2c3d4e5f6
Revises: c9f8a8f6f0a1
Create Date: 2026-02-14 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c9f8a8f6f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID"),
        sa.Column(
            "name",
            sa.Enum("GOOGLE", "OPENAI", name="providername"),
            nullable=False,
            comment="Name",
        ),
        sa.Column(
            "api_key_encrypted",
            sa.String(),
            nullable=False,
            comment="Encrypted API key",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="Is active"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Created at",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Updated at",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("providers")
    sa.Enum(name="providername").drop(op.get_bind())
