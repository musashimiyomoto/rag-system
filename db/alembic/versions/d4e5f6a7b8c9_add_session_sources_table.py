"""Add session_sources table

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-02-14 21:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_session_source_fk() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for foreign_key in inspector.get_foreign_keys("sessions"):
        referred_table = foreign_key.get("referred_table")
        columns = foreign_key.get("constrained_columns")
        if referred_table == "sources" and columns == ["source_id"]:
            name = foreign_key.get("name")
            if name:
                op.drop_constraint(name, "sessions", type_="foreignkey")


def upgrade() -> None:
    op.create_table(
        "session_sources",
        sa.Column("session_id", sa.Integer(), nullable=False, comment="Session ID"),
        sa.Column("source_id", sa.Integer(), nullable=False, comment="Source ID"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Created at",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("session_id", "source_id"),
        sa.UniqueConstraint("session_id", "source_id"),
    )
    op.create_index(
        op.f("ix_session_sources_session_id"),
        "session_sources",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_sources_source_id"),
        "session_sources",
        ["source_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO session_sources (session_id, source_id, created_at)
        SELECT id, source_id, created_at
        FROM sessions
        """
    )

    _drop_session_source_fk()
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("source_id")


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(
            sa.Column("source_id", sa.Integer(), nullable=True, comment="Source ID")
        )

    op.execute(
        """
        UPDATE sessions AS s
        SET source_id = grouped.source_id
        FROM (
            SELECT session_id, MIN(source_id) AS source_id
            FROM session_sources
            GROUP BY session_id
        ) AS grouped
        WHERE s.id = grouped.session_id
        """
    )

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.alter_column(
            "source_id",
            existing_type=sa.Integer(),
            nullable=False,
            comment="Source ID",
        )

    op.create_foreign_key(
        "fk_sessions_source_id_sources",
        "sessions",
        "sources",
        ["source_id"],
        ["id"],
    )

    op.drop_index(op.f("ix_session_sources_source_id"), table_name="session_sources")
    op.drop_index(op.f("ix_session_sources_session_id"), table_name="session_sources")
    op.drop_table("session_sources")
