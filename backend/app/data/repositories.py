"""Data layer: the only code that queries finance tables.

A repository is created for one user and adds ``owner_id = :user`` to every
query, so services, agents and API routes cannot accidentally read or change
another user's records.
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.agent_run import AgentRun
from backend.app.models.finance import Account, Budget, Holding, Transaction


class FinanceRepository:
    def __init__(self, db: Session, owner_id: int) -> None:
        self.db = db
        self.owner_id = owner_id

    # ---------------------------------------------------------------- write
    def add(self, obj: Account | Transaction | Budget | Holding | AgentRun) -> None:
        if obj.owner_id != self.owner_id:
            raise PermissionError("object does not belong to this user")
        self.db.add(obj)

    def delete(self, obj: Account | Transaction | Budget | Holding) -> None:
        if obj.owner_id != self.owner_id:
            raise PermissionError("object does not belong to this user")
        self.db.delete(obj)

    # ------------------------------------------------------------- accounts
    def accounts(self) -> Sequence[Account]:
        return self.db.scalars(select(Account).where(Account.owner_id == self.owner_id).order_by(Account.id)).all()

    def get_account(self, account_id: int) -> Account | None:
        return self.db.scalar(select(Account).where(Account.id == account_id, Account.owner_id == self.owner_id))

    def account_name_exists(self, name: str) -> bool:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Account)
                .where(Account.owner_id == self.owner_id, func.lower(Account.name) == name.lower())
            )
            or 0
        ) > 0

    def account_balances(self) -> dict[int, Decimal]:
        rows = self.db.execute(
            select(Transaction.account_id, func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.owner_id == self.owner_id)
            .group_by(Transaction.account_id)
        ).all()
        movements = {account_id: Decimal(total) for account_id, total in rows}
        return {a.id: Decimal(a.opening_balance) + movements.get(a.id, Decimal("0")) for a in self.accounts()}

    # --------------------------------------------------------- transactions
    def _transaction_filters(
        self,
        *,
        account_id: int | None = None,
        category: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list:
        filters = [Transaction.owner_id == self.owner_id]
        if account_id is not None:
            filters.append(Transaction.account_id == account_id)
        if category is not None:
            filters.append(Transaction.category == category)
        if start is not None:
            filters.append(Transaction.booked_on >= start)
        if end is not None:
            filters.append(Transaction.booked_on <= end)
        return filters

    def transactions(
        self,
        *,
        account_id: int | None = None,
        category: str | None = None,
        start: date | None = None,
        end: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        query = (
            select(Transaction)
            .where(*self._transaction_filters(account_id=account_id, category=category, start=start, end=end))
            .order_by(Transaction.booked_on.desc(), Transaction.id.desc())
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        return self.db.scalars(query).all()

    def count_transactions(self, **filters) -> int:
        return self.db.scalar(select(func.count()).select_from(Transaction).where(*self._transaction_filters(**filters))) or 0

    def get_transaction(self, transaction_id: int) -> Transaction | None:
        return self.db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.owner_id == self.owner_id))

    def spending_by_category(self, start: date, end: date) -> dict[str, Decimal]:
        rows = self.db.execute(
            select(Transaction.category, func.sum(Transaction.amount))
            .where(*self._transaction_filters(start=start, end=end), Transaction.amount < 0)
            .group_by(Transaction.category)
        ).all()
        return {category: -Decimal(total) for category, total in rows}

    # -------------------------------------------------------------- budgets
    def budgets(self) -> Sequence[Budget]:
        return self.db.scalars(select(Budget).where(Budget.owner_id == self.owner_id).order_by(Budget.category)).all()

    def get_budget(self, category: str) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.owner_id == self.owner_id, Budget.category == category))

    # ------------------------------------------------------------- holdings
    def holdings(self) -> Sequence[Holding]:
        return self.db.scalars(select(Holding).where(Holding.owner_id == self.owner_id).order_by(Holding.symbol)).all()

    def get_holding(self, holding_id: int) -> Holding | None:
        return self.db.scalar(select(Holding).where(Holding.id == holding_id, Holding.owner_id == self.owner_id))

    def get_holding_by_symbol(self, symbol: str) -> Holding | None:
        return self.db.scalar(select(Holding).where(Holding.owner_id == self.owner_id, Holding.symbol == symbol))

    # ----------------------------------------------------------- agent runs
    def agent_runs(self, limit: int, offset: int) -> Sequence[AgentRun]:
        return self.db.scalars(
            select(AgentRun)
            .where(AgentRun.owner_id == self.owner_id)
            .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()

    def get_agent_run(self, run_id: int) -> AgentRun | None:
        return self.db.scalar(select(AgentRun).where(AgentRun.id == run_id, AgentRun.owner_id == self.owner_id))
