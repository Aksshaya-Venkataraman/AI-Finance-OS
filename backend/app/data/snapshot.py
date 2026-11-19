"""Read-only, plain-Python view of one user's finances for the agent layer.

Agents receive a snapshot instead of a database session: they cannot write,
cannot see other users' data, and are trivially unit-testable.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from backend.app.data.repositories import FinanceRepository


@dataclass(frozen=True)
class AccountView:
    id: int
    name: str
    account_type: str
    currency: str
    balance: Decimal


@dataclass(frozen=True)
class TransactionView:
    booked_on: date
    amount: Decimal
    category: str
    description: str
    account_id: int


@dataclass(frozen=True)
class HoldingView:
    symbol: str
    name: str
    asset_class: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return (self.quantity * self.current_price).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class FinanceSnapshot:
    as_of: date
    accounts: list[AccountView] = field(default_factory=list)
    transactions: list[TransactionView] = field(default_factory=list)
    budgets: dict[str, Decimal] = field(default_factory=dict)
    holdings: list[HoldingView] = field(default_factory=list)

    @property
    def currency(self) -> str | None:
        """The single currency used by all accounts, or None if they are mixed."""
        currencies = {a.currency for a in self.accounts}
        return currencies.pop() if len(currencies) == 1 else None


def build_snapshot(repo: FinanceRepository, as_of: date | None = None, days: int = 400) -> FinanceSnapshot:
    as_of = as_of or date.today()
    balances = repo.account_balances()
    accounts = [AccountView(a.id, a.name, a.account_type, a.currency, balances.get(a.id, Decimal("0"))) for a in repo.accounts()]
    transactions = [
        TransactionView(t.booked_on, Decimal(t.amount), t.category, t.description, t.account_id)
        for t in repo.transactions(start=as_of - timedelta(days=days), end=as_of)
    ]
    holdings = [
        HoldingView(h.symbol, h.name, h.asset_class, Decimal(h.quantity), Decimal(h.cost_basis), Decimal(h.current_price))
        for h in repo.holdings()
    ]
    budgets = {b.category: Decimal(b.monthly_limit) for b in repo.budgets()}
    return FinanceSnapshot(as_of, accounts, transactions, budgets, holdings)
