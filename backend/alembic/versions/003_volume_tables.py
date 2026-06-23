"""Add volume_history and volume_forecast tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "volume_history",
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("volume_usd", sa.Numeric(24, 2), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("instrument_id", "ts", "source"),
    )
    op.create_index("ix_volume_history_inst_ts", "volume_history", ["instrument_id", "ts"])

    op.create_table(
        "volume_forecast",
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("horizon_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("volume_p25", sa.Numeric(24, 2), nullable=False),
        sa.Column("volume_p50", sa.Numeric(24, 2), nullable=False),
        sa.Column("volume_p75", sa.Numeric(24, 2), nullable=False),
        sa.PrimaryKeyConstraint("instrument_id", "generated_at", "horizon_ts"),
    )
    op.create_index(
        "ix_volume_forecast_inst_gen",
        "volume_forecast",
        ["instrument_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_table("volume_forecast")
    op.drop_table("volume_history")
