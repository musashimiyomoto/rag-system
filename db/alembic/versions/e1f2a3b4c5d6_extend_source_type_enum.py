"""Extend source type enum

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-02-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'MD'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'DOCX'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'RTF'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'ODT'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'EPUB'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'HTML'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'HTM'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'PPTX'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'XLSX'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'EML'")


def downgrade() -> None:
    # PostgreSQL enum labels cannot be removed safely without recreating the type.
    pass
