"""finance data, agent runs, hashed password-reset tokens

Revision ID: 7c1e4a9b2f60
Revises: d3c649f0e4b0
Create Date: 2026-11-19 15:00:00

- Adds accounts, transactions, budgets, holdings and agent_runs.
- Password-reset tokens are now stored as SHA-256 hashes. Existing plain-text
  tokens are invalidated (marked used) before the column is renamed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7c1e4a9b2f60"
down_revision: str | Sequence[str] | None = "d3c649f0e4b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(14, 2)
JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # --- password reset tokens: plain text -> SHA-256 hash ------------------
    op.execute("UPDATE password_reset_tokens SET used = true WHERE used = false")
    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.alter_column(
        "password_reset_tokens",
        "token",
        new_column_name="token_hash",
        type_=sa.String(64),
        existing_type=sa.String(255),
        existing_nullable=False,
        postgresql_using="left(token, 64)",
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    # --- finance data ---------------------------------------------------------
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("opening_balance", MONEY, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("owner_id", "name", name="uq_accounts_owner_name"),
    )
    op.create_index("ix_accounts_owner_id", "accounts", ["owner_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("booked_on", sa.Date(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_transactions_owner_id", "transactions", ["owner_id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_category", "transactions", ["category"])
    op.create_index("ix_transactions_owner_date", "transactions", ["owner_id", "booked_on"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("monthly_limit", MONEY, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("owner_id", "category", name="uq_budgets_owner_category"),
        sa.CheckConstraint("monthly_limit > 0", name="ck_budgets_positive_limit"),
    )
    op.create_index("ix_budgets_owner_id", "budgets", ["owner_id"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(15), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("cost_basis", MONEY, nullable=False),
        sa.Column("current_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("owner_id", "symbol", name="uq_holdings_owner_symbol"),
        sa.CheckConstraint("quantity > 0", name="ck_holdings_positive_quantity"),
    )
    op.create_index("ix_holdings_owner_id", "holdings", ["owner_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("intents", JSON, nullable=False),
        sa.Column("steps", JSON, nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("llm_used", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_runs_owner_id", "agent_runs", ["owner_id"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("holdings")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("accounts")

    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.alter_column(
        "password_reset_tokens",
        "token_hash",
        new_column_name="token",
        type_=sa.String(255),
        existing_type=sa.String(64),
        existing_nullable=False,
    )
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)
