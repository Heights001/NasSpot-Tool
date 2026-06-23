"""Add TA signal columns to intel_snapshot

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("intel_snapshot", sa.Column("rsi_14", sa.Numeric(6, 2), nullable=True))
    op.add_column("intel_snapshot", sa.Column("bb_pct_b", sa.Numeric(7, 4), nullable=True))
    op.add_column("intel_snapshot", sa.Column("sma_trend", sa.String(10), nullable=True))
    op.add_column("intel_snapshot", sa.Column("ta_composite", sa.String(20), nullable=True))
    op.add_column("intel_snapshot", sa.Column("ta_reasoning", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("intel_snapshot", "ta_reasoning")
    op.drop_column("intel_snapshot", "ta_composite")
    op.drop_column("intel_snapshot", "sma_trend")
    op.drop_column("intel_snapshot", "bb_pct_b")
    op.drop_column("intel_snapshot", "rsi_14")
