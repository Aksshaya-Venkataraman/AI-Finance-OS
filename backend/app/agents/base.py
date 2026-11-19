"""Agent contract and shared helpers.

Agents do all of the arithmetic in plain Python on a read-only snapshot. The
language model (if enabled) only turns their structured findings into prose,
so it can never invent a balance or miscalculate a total.
"""

import calendar
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, ClassVar

from backend.app.data.snapshot import FinanceSnapshot, TransactionView

# Movements between the user's own accounts are not spending.
NON_SPENDING = frozenset({"transfer", "savings"})
_SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "INR": "₹", "JPY": "¥"}


@dataclass
class AgentResult:
    agent: str
    summary: str
    facts: dict[str, Any]
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Agent(ABC):
    name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def run(self, snapshot: FinanceSnapshot) -> AgentResult: ...


# ----------------------------------------------------------------- helpers
def num(value: Decimal | float | int) -> float:
    """Round to 2 dp for JSON facts (exact decimal rounding, then float)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def fmt_money(value: Decimal | float, currency: str | None) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    body = f"{abs(amount):,.2f}"
    if currency in _SYMBOLS:
        return f"{sign}{_SYMBOLS[currency]}{body}"
    return f"{sign}{body} {currency}" if currency else f"{sign}{body}"


def month_start(day: date) -> date:
    return day.replace(day=1)


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def days_in_month(day: date) -> int:
    return calendar.monthrange(day.year, day.month)[1]


def expenses(transactions: list[TransactionView], start: date, end: date) -> list[TransactionView]:
    return [t for t in transactions if start <= t.booked_on <= end and t.amount < 0 and t.category not in NON_SPENDING]


def total_spent(transactions: list[TransactionView]) -> Decimal:
    return -sum((t.amount for t in transactions), Decimal("0"))


def by_category(transactions: list[TransactionView]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for t in transactions:
        totals[t.category] = totals.get(t.category, Decimal("0")) - t.amount
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def previous_month_same_period(as_of: date) -> tuple[date, date]:
    """The same days-of-month in the previous month, for a fair comparison."""
    start = add_months(month_start(as_of), -1)
    end = min(start + timedelta(days=as_of.day - 1), month_end(start))
    return start, end
