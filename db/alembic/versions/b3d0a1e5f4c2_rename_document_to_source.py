"""Rename document domain to source

Revision ID: b3d0a1e5f4c2
Revises: 1028136b2266
Create Date: 2026-02-14 17:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d0a1e5f4c2"
down_revision: Union[str, None] = "1028136b2266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_session_fk() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for foreign_key in inspector.get_foreign_keys("sessions"):
        referred_table = foreign_key.get("referred_table")
        columns = foreign_key.get("constrained_columns")
        if referred_table in {"documents", "sources"} and columns in (
            ["document_id"],
            ["source_id"],
        ):
            name = foreign_key.get("name")
            if name:
                op.drop_constraint(name, "sessions", type_="foreignkey")


def _create_session_fk() -> None:
    op.create_foreign_key(
        "fk_sessions_source_id_sources",
        "sessions",
        "sources",
        ["source_id"],
        ["id"],
    )


def upgrade() -> None:
    _drop_session_fk()

    op.execute("ALTER TYPE documenttype RENAME TO sourcetype")
    op.execute("ALTER TYPE documentstatus RENAME TO sourcestatus")

    op.rename_table("documents", "sources")

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.alter_column(
            "document_id",
            new_column_name="source_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            comment="Source ID",
        )

    _create_session_fk()


def downgrade() -> None:
    _drop_session_fk()

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.alter_column(
            "source_id",
            new_column_name="document_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            comment="Document ID",
        )

    op.rename_table("sources", "documents")

    op.execute("ALTER TYPE sourcetype RENAME TO documenttype")
    op.execute("ALTER TYPE sourcestatus RENAME TO documentstatus")

    op.create_foreign_key(
        "fk_sessions_document_id_documents",
        "sessions",
        "documents",
        ["document_id"],
        ["id"],
    )
