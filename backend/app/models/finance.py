"""Personal-finance data: accounts, transactions, budgets and investment holdings.

Every row belongs to exactly one user (``owner_id``); the data layer always
filters on it, so one user can never read or change another user's data.
Money is stored as NUMERIC, never as floating point.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base, utcnow

MONEY = Numeric(14, 2)

CATEGORIES = (
    "income",
    "housing",
    "utilities",
    "groceries",
    "dining",
    "transport",
    "shopping",
    "health",
    "entertainment",
    "travel",
    "education",
    "subscriptions",
    "savings",
    "transfer",
    "other",
)
ACCOUNT_TYPES = ("current", "savings", "credit_card", "investment", "cash")
ASSET_CLASSES = ("equity", "bond", "fund", "cash", "crypto", "property", "other")


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_accounts_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    account_type: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_owner_date", "owner_id", "booked_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    booked_on: Mapped[date] = mapped_column(Date)
    # Positive = money in, negative = money out.
    amount: Mapped[Decimal] = mapped_column(MONEY)
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("owner_id", "category", name="uq_budgets_owner_category"),
        CheckConstraint("monthly_limit > 0", name="ck_budgets_positive_limit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    monthly_limit: Mapped[Decimal] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("owner_id", "symbol", name="uq_holdings_owner_symbol"),
        CheckConstraint("quantity > 0", name="ck_holdings_positive_quantity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(15))
    name: Mapped[str] = mapped_column(String(100))
    asset_class: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    cost_basis: Mapped[Decimal] = mapped_column(MONEY)  # total amount paid
    current_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
