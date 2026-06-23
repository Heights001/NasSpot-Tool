"""Add price_intraday, ml_model_meta, ml_prediction tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_intraday",
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low",  sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "ts"),
    )
    op.create_index("ix_price_intraday_inst_ts", "price_intraday", ["instrument_id", "ts"])

    op.create_table(
        "ml_model_meta",
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("horizon_minutes", sa.Integer, nullable=False),
        sa.Column("trained_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("n_samples", sa.Integer),
        sa.Column("cv_accuracy", sa.Numeric(5, 4)),
        sa.Column("feature_names_json", sa.Text),
        sa.Column("coef_json", sa.Text),
        sa.Column("intercept", sa.Numeric(12, 8)),
        sa.Column("scaler_mean_json", sa.Text),
        sa.Column("scaler_scale_json", sa.Text),
        sa.PrimaryKeyConstraint("instrument_id", "horizon_minutes"),
    )

    op.create_table(
        "ml_prediction",
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("horizon_minutes", sa.Integer, nullable=False),
        sa.Column("predicted_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("prob_up", sa.Numeric(5, 4), nullable=False),
        sa.Column("signal", sa.String(10), nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.PrimaryKeyConstraint("instrument_id", "horizon_minutes"),
    )


def downgrade() -> None:
    op.drop_table("ml_prediction")
    op.drop_table("ml_model_meta")
    op.drop_index("ix_price_intraday_inst_ts", "price_intraday")
    op.drop_table("price_intraday")
