"""Add source_dbs table and DB source types

Revision ID: aa11bb22cc33
Revises: f7a8b9c0d1e2
Create Date: 2026-02-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa11bb22cc33"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'POSTGRES'")
    op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'CLICKHOUSE'")

    op.create_table(
        "source_dbs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID"),
        sa.Column("source_id", sa.Integer(), nullable=False, comment="Source ID"),
        sa.Column(
            "db_type",
            sa.Enum("POSTGRES", "CLICKHOUSE", name="sourcetype"),
            nullable=False,
            comment="DB type",
        ),
        sa.Column(
            "connection_encrypted",
            sa.String(),
            nullable=False,
            comment="Encrypted connection",
        ),
        sa.Column("schema_name", sa.String(), nullable=False, comment="Schema name"),
        sa.Column("table_name", sa.String(), nullable=False, comment="Table name"),
        sa.Column("id_field", sa.String(), nullable=False, comment="ID field"),
        sa.Column("search_field", sa.String(), nullable=False, comment="Search field"),
        sa.Column("filter_fields", sa.JSON(), nullable=False, comment="Filter fields"),
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
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )


def downgrade() -> None:
    op.drop_table("source_dbs")
    # PostgreSQL enum labels cannot be removed safely without recreating the type.
