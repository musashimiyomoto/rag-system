"""Add ollama provider enum value

Revision ID: 3f2c1b0a9d8e
Revises: aa11bb22cc33
Create Date: 2026-03-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f2c1b0a9d8e"
down_revision: Union[str, None] = "aa11bb22cc33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'OLLAMA'")


def downgrade() -> None:
    # PostgreSQL enum labels cannot be removed safely without recreating the type.
    pass
