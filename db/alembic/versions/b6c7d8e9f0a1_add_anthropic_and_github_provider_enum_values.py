"""Add anthropic and github provider enum values

Revision ID: b6c7d8e9f0a1
Revises: 3f2c1b0a9d8e
Create Date: 2026-03-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "3f2c1b0a9d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'ANTHROPIC'")
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'GITHUB'")


def downgrade() -> None:
    # PostgreSQL enum labels cannot be removed safely without recreating the type.
    pass
