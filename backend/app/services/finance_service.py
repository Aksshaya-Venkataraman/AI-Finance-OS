"""Business rules for accounts, transactions, budgets and holdings."""

import csv
import io
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from backend.app.agents.base import by_category, expenses, month_start
from backend.app.agents.budget import budget_status
from backend.app.data.repositories import FinanceRepository
from backend.app.data.snapshot import TransactionView
from backend.app.models.finance import Account, Budget, Holding, Transaction
from backend.app.schemas.finance import (
    AccountCreate,
    AccountOut,
    BudgetStatus,
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
    TransactionCreate,
    TransactionUpdate,
)
from backend.app.services.errors import ConflictError, NotFoundError, ValidationFailed

MAX_IMPORT_ROWS = 5000
CSV_COLUMNS = ("date", "amount", "description", "category")


# ---------------------------------------------------------------- accounts
def list_accounts(repo: FinanceRepository) -> list[AccountOut]:
    balances = repo.account_balances()
    return [AccountOut.model_validate({**_columns(a), "balance": balances.get(a.id, Decimal("0"))}) for a in repo.accounts()]


def create_account(repo: FinanceRepository, data: AccountCreate) -> AccountOut:
    if repo.account_name_exists(data.name):
        raise ConflictError("An account with this name already exists")
    account = Account(owner_id=repo.owner_id, **data.model_dump())
    repo.add(account)
    repo.db.commit()
    return AccountOut.model_validate({**_columns(account), "balance": account.opening_balance})


def delete_account(repo: FinanceRepository, account_id: int) -> None:
    account = repo.get_account(account_id)
    if account is None:
        raise NotFoundError("Account not found")
    for tx in repo.transactions(account_id=account_id):
        repo.delete(tx)
    repo.delete(account)
    repo.db.commit()


# ------------------------------------------------------------ transactions
def create_transaction(repo: FinanceRepository, data: TransactionCreate) -> Transaction:
    # The account must belong to the caller: an id from another user is "not found".
    if repo.get_account(data.account_id) is None:
        raise NotFoundError("Account not found")
    tx = Transaction(owner_id=repo.owner_id, **data.model_dump())
    repo.add(tx)
    repo.db.commit()
    return tx


def update_transaction(repo: FinanceRepository, transaction_id: int, data: TransactionUpdate) -> Transaction:
    tx = repo.get_transaction(transaction_id)
    if tx is None:
        raise NotFoundError("Transaction not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tx, field, value)
    repo.db.commit()
    return tx


def delete_transaction(repo: FinanceRepository, transaction_id: int) -> None:
    tx = repo.get_transaction(transaction_id)
    if tx is None:
        raise NotFoundError("Transaction not found")
    repo.delete(tx)
    repo.db.commit()


def import_transactions_csv(repo: FinanceRepository, account_id: int, content: bytes) -> int:
    """All-or-nothing CSV import (columns: date, amount, description, category)."""
    if repo.get_account(account_id) is None:
        raise NotFoundError("Account not found")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationFailed("File must be UTF-8 encoded CSV", []) from None

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or [h.strip().lower() for h in reader.fieldnames] != list(CSV_COLUMNS):
        raise ValidationFailed(f"CSV header must be exactly: {','.join(CSV_COLUMNS)}", [])

    rows, errors = [], []
    for line, raw in enumerate(reader, start=2):
        if len(rows) + len(errors) >= MAX_IMPORT_ROWS:
            raise ValidationFailed(f"CSV has more than {MAX_IMPORT_ROWS} rows", [])
        values = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        try:
            rows.append(
                TransactionCreate(
                    account_id=account_id,
                    booked_on=values["date"],
                    amount=values["amount"],
                    description=values["description"],
                    category=values["category"].lower(),
                )
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            errors.append(f"line {line}: {'.'.join(str(p) for p in first['loc'])}: {first['msg']}")
    if errors:
        raise ValidationFailed("CSV contains invalid rows; nothing was imported", errors[:20])
    if not rows:
        raise ValidationFailed("CSV contains no rows", [])

    for row in rows:
        repo.add(Transaction(owner_id=repo.owner_id, **row.model_dump()))
    repo.db.commit()
    return len(rows)


# ----------------------------------------------------------------- budgets
def budget_overview(repo: FinanceRepository, today: date | None = None) -> list[BudgetStatus]:
    today = today or date.today()
    start = month_start(today)
    views = [
        TransactionView(t.booked_on, Decimal(t.amount), t.category, t.description, t.account_id)
        for t in repo.transactions(start=start, end=today)
    ]
    spent = by_category(expenses(views, start, today))
    result = []
    for budget in repo.budgets():
        used = spent.get(budget.category, Decimal("0"))
        limit = Decimal(budget.monthly_limit)
        result.append(
            BudgetStatus(
                category=budget.category,
                monthly_limit=limit,
                spent_this_month=used,
                remaining=limit - used,
                percent_used=round(float(used / limit * 100), 1),
                status=budget_status(used, limit),
            )
        )
    return result


def upsert_budget(repo: FinanceRepository, category: str, monthly_limit: Decimal) -> Budget:
    budget = repo.get_budget(category)
    if budget is None:
        budget = Budget(owner_id=repo.owner_id, category=category, monthly_limit=monthly_limit)
        repo.add(budget)
    else:
        budget.monthly_limit = monthly_limit
    repo.db.commit()
    return budget


def delete_budget(repo: FinanceRepository, category: str) -> None:
    budget = repo.get_budget(category)
    if budget is None:
        raise NotFoundError("Budget not found")
    repo.delete(budget)
    repo.db.commit()


# ---------------------------------------------------------------- holdings
def holding_out(h: Holding) -> HoldingOut:
    value = (Decimal(h.quantity) * Decimal(h.current_price)).quantize(Decimal("0.01"))
    return HoldingOut.model_validate({**_columns(h), "market_value": value, "unrealised_gain": value - Decimal(h.cost_basis)})


def create_holding(repo: FinanceRepository, data: HoldingCreate) -> HoldingOut:
    if repo.get_holding_by_symbol(data.symbol) is not None:
        raise ConflictError("This symbol is already in your portfolio; update it instead")
    holding = Holding(owner_id=repo.owner_id, **data.model_dump())
    repo.add(holding)
    repo.db.commit()
    return holding_out(holding)


def update_holding(repo: FinanceRepository, holding_id: int, data: HoldingUpdate) -> HoldingOut:
    holding = repo.get_holding(holding_id)
    if holding is None:
        raise NotFoundError("Holding not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(holding, field, value)
    repo.db.commit()
    return holding_out(holding)


def delete_holding(repo: FinanceRepository, holding_id: int) -> None:
    holding = repo.get_holding(holding_id)
    if holding is None:
        raise NotFoundError("Holding not found")
    repo.delete(holding)
    repo.db.commit()


def _columns(obj: object) -> dict:
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}  # type: ignore[attr-defined]
