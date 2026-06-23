"""Initial schema: instruments, latest_price, price_history, source_quote

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, unique=True),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("asset_class", sa.String(10), nullable=False),
        sa.Column("quote_ccy", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("provider_symbol_twelvedata", sa.String(30)),
        sa.Column("provider_symbol_coingecko", sa.String(50)),
        sa.Column("display_precision", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_peg_watch", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])

    op.create_table(
        "latest_price",
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), primary_key=True),
        sa.Column("price", sa.Numeric(20, 10), nullable=False),
        sa.Column("bid", sa.Numeric(20, 10)),
        sa.Column("ask", sa.Numeric(20, 10)),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_ts", sa.TIMESTAMP(timezone=True)),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_realtime", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("market_state", sa.String(20), nullable=False, server_default="open"),
        sa.Column("change_1h", sa.Numeric(20, 10)),
        sa.Column("change_24h", sa.Numeric(20, 10)),
        sa.Column("change_7d", sa.Numeric(20, 10)),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(20, 10), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
    )
    op.create_index("ix_price_history_instrument_ts", "price_history", ["instrument_id", "ts"])

    op.create_table(
        "source_quote",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(20, 10), nullable=False),
        sa.Column("source_ts", sa.TIMESTAMP(timezone=True)),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_source_quote_instrument_source", "source_quote", ["instrument_id", "source"]
    )

    op.bulk_insert(
        sa.table(
            "instruments",
            sa.column("symbol", sa.String),
            sa.column("display_name", sa.String),
            sa.column("asset_class", sa.String),
            sa.column("quote_ccy", sa.String),
            sa.column("provider_symbol_twelvedata", sa.String),
            sa.column("provider_symbol_coingecko", sa.String),
            sa.column("display_precision", sa.Integer),
            sa.column("is_active", sa.Boolean),
            sa.column("sort_order", sa.Integer),
            sa.column("is_peg_watch", sa.Boolean),
        ),
        [
            # FX Majors
            {"symbol": "EUR/USD", "display_name": "Euro / US Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "EUR/USD", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 1, "is_peg_watch": False},
            {"symbol": "USD/JPY", "display_name": "US Dollar / Japanese Yen", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/JPY", "provider_symbol_coingecko": None, "display_precision": 3, "is_active": True, "sort_order": 2, "is_peg_watch": False},
            {"symbol": "GBP/USD", "display_name": "British Pound / US Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "GBP/USD", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 3, "is_peg_watch": False},
            {"symbol": "USD/CHF", "display_name": "US Dollar / Swiss Franc", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/CHF", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 4, "is_peg_watch": False},
            {"symbol": "AUD/USD", "display_name": "Australian Dollar / US Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "AUD/USD", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 5, "is_peg_watch": False},
            {"symbol": "USD/CAD", "display_name": "US Dollar / Canadian Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/CAD", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 6, "is_peg_watch": False},
            {"symbol": "NZD/USD", "display_name": "New Zealand Dollar / US Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "NZD/USD", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 7, "is_peg_watch": False},
            # FX Crosses
            {"symbol": "EUR/GBP", "display_name": "Euro / British Pound", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "EUR/GBP", "provider_symbol_coingecko": None, "display_precision": 5, "is_active": True, "sort_order": 8, "is_peg_watch": False},
            {"symbol": "EUR/JPY", "display_name": "Euro / Japanese Yen", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "EUR/JPY", "provider_symbol_coingecko": None, "display_precision": 3, "is_active": True, "sort_order": 9, "is_peg_watch": False},
            {"symbol": "GBP/JPY", "display_name": "British Pound / Japanese Yen", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "GBP/JPY", "provider_symbol_coingecko": None, "display_precision": 3, "is_active": True, "sort_order": 10, "is_peg_watch": False},
            # Dollar gauge
            {"symbol": "DXY", "display_name": "US Dollar Index", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "DXY", "provider_symbol_coingecko": None, "display_precision": 3, "is_active": True, "sort_order": 11, "is_peg_watch": False},
            # EM
            {"symbol": "USD/CNH", "display_name": "US Dollar / Offshore Chinese Yuan", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/CNH", "provider_symbol_coingecko": None, "display_precision": 4, "is_active": True, "sort_order": 12, "is_peg_watch": False},
            {"symbol": "USD/MXN", "display_name": "US Dollar / Mexican Peso", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/MXN", "provider_symbol_coingecko": None, "display_precision": 4, "is_active": True, "sort_order": 13, "is_peg_watch": False},
            {"symbol": "USD/ZAR", "display_name": "US Dollar / South African Rand", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/ZAR", "provider_symbol_coingecko": None, "display_precision": 4, "is_active": True, "sort_order": 14, "is_peg_watch": False},
            {"symbol": "USD/SGD", "display_name": "US Dollar / Singapore Dollar", "asset_class": "fx", "quote_ccy": "USD", "provider_symbol_twelvedata": "USD/SGD", "provider_symbol_coingecko": None, "display_precision": 4, "is_active": True, "sort_order": 15, "is_peg_watch": False},
            # Crypto majors
            {"symbol": "BTC", "display_name": "Bitcoin", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "bitcoin", "display_precision": 2, "is_active": True, "sort_order": 20, "is_peg_watch": False},
            {"symbol": "ETH", "display_name": "Ethereum", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "ethereum", "display_precision": 2, "is_active": True, "sort_order": 21, "is_peg_watch": False},
            # Large caps
            {"symbol": "SOL", "display_name": "Solana", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "solana", "display_precision": 4, "is_active": True, "sort_order": 22, "is_peg_watch": False},
            {"symbol": "XRP", "display_name": "XRP", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "ripple", "display_precision": 4, "is_active": True, "sort_order": 23, "is_peg_watch": False},
            {"symbol": "BNB", "display_name": "BNB", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "binancecoin", "display_precision": 4, "is_active": True, "sort_order": 24, "is_peg_watch": False},
            # Peg watch
            {"symbol": "USDT", "display_name": "Tether", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "tether", "display_precision": 6, "is_active": True, "sort_order": 25, "is_peg_watch": True},
            {"symbol": "USDC", "display_name": "USD Coin", "asset_class": "crypto", "quote_ccy": "USD", "provider_symbol_twelvedata": None, "provider_symbol_coingecko": "usd-coin", "display_precision": 6, "is_active": True, "sort_order": 26, "is_peg_watch": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("source_quote")
    op.drop_table("price_history")
    op.drop_table("latest_price")
    op.drop_table("instruments")
