"""create application configuration tables

Revision ID: f70fdc262bd9
Revises:
Create Date: 2026-08-24 13:28:18.592849

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f70fdc262bd9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "chainpulse"


def upgrade() -> None:
    op.execute("CREATE SCHEMA chainpulse")

    op.create_table(
        "watchlist",
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("address", sa.String(length=42), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "chain_id",
            "address",
            name="pk_watchlist",
        ),
        sa.CheckConstraint(
            "chain_id > 0",
            name="ck_watchlist_chain_id_positive",
        ),
        sa.CheckConstraint(
            "address ~ '^0x[0-9a-f]{40}$'",
            name="ck_watchlist_address_format",
        ),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_watchlist_chain_active",
        "watchlist",
        ["chain_id", "is_active"],
        schema=SCHEMA,
    )

    op.create_table(
        "ingestion_checkpoints",
        sa.Column(
            "pipeline_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column(
            "block_hash",
            sa.String(length=66),
            nullable=False,
        ),
        sa.Column(
            "finality_status",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "pipeline_name",
            "chain_id",
            name="pk_ingestion_checkpoints",
        ),
        sa.CheckConstraint(
            "chain_id > 0",
            name="ck_ingestion_checkpoints_chain_id_positive",
        ),
        sa.CheckConstraint(
            "block_number >= 0",
            name="ck_ingestion_checkpoints_block_number_nonnegative",
        ),
        sa.CheckConstraint(
            "block_hash ~ '^0x[0-9a-f]{64}$'",
            name="ck_ingestion_checkpoints_block_hash_format",
        ),
        sa.CheckConstraint(
            "finality_status IN ('latest', 'safe', 'finalized', 'orphaned')",
            name="ck_ingestion_checkpoints_finality_status",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "app_config",
        sa.Column(
            "namespace",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "config_key",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "config_value",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "namespace",
            "config_key",
            name="pk_app_config",
        ),
        sa.CheckConstraint(
            "length(namespace) > 0",
            name="ck_app_config_namespace_not_empty",
        ),
        sa.CheckConstraint(
            "length(config_key) > 0",
            name="ck_app_config_key_not_empty",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("app_config", schema=SCHEMA)
    op.drop_table(
        "ingestion_checkpoints",
        schema=SCHEMA,
    )
    op.drop_table("watchlist", schema=SCHEMA)
    op.execute("DROP SCHEMA chainpulse")
