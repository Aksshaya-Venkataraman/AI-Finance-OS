"""Accounts, transactions, budgets and holdings. Every route is scoped to the caller."""

from collections.abc import Callable
from datetime import date
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.core.rate_limit import limit_by_user
from backend.app.data.repositories import FinanceRepository
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.finance import (
    AccountCreate,
    AccountOut,
    BudgetStatus,
    BudgetUpsert,
    Category,
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
    ImportResult,
    TransactionCreate,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)
from backend.app.services import finance_service as svc
from backend.app.services.errors import ConflictError, NotFoundError, ValidationFailed

router = APIRouter(dependencies=[Depends(limit_by_user("api", "API_RATE_LIMIT"))])
MAX_CSV_BYTES = 1_000_000


def get_repo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FinanceRepository:
    return FinanceRepository(db, current_user.id)


def service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except NotFoundError as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from None
        except ConflictError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
        except ValidationFailed as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {"message": str(e), "errors": e.errors}) from None

    return wrapper


# ---------------------------------------------------------------- accounts
@router.get("/accounts", response_model=list[AccountOut], tags=["Accounts"])
def list_accounts(repo: FinanceRepository = Depends(get_repo)):
    return svc.list_accounts(repo)


@router.post("/accounts", response_model=AccountOut, status_code=201, tags=["Accounts"])
@service_errors
def create_account(body: AccountCreate, repo: FinanceRepository = Depends(get_repo)):
    return svc.create_account(repo, body)


@router.delete("/accounts/{account_id}", status_code=204, tags=["Accounts"])
@service_errors
def delete_account(account_id: int, repo: FinanceRepository = Depends(get_repo)):
    svc.delete_account(repo, account_id)
    return Response(status_code=204)


# ------------------------------------------------------------ transactions
@router.get("/transactions", response_model=TransactionPage, tags=["Transactions"])
def list_transactions(
    repo: FinanceRepository = Depends(get_repo),
    account_id: int | None = Query(default=None, gt=0),
    category: Category | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    filters = {"account_id": account_id, "category": category, "start": start, "end": end}
    items = repo.transactions(**filters, limit=limit, offset=offset)
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        total=repo.count_transactions(**filters),
        limit=limit,
        offset=offset,
    )


@router.post("/transactions", response_model=TransactionOut, status_code=201, tags=["Transactions"])
@service_errors
def create_transaction(body: TransactionCreate, repo: FinanceRepository = Depends(get_repo)):
    return svc.create_transaction(repo, body)


@router.patch("/transactions/{transaction_id}", response_model=TransactionOut, tags=["Transactions"])
@service_errors
def update_transaction(transaction_id: int, body: TransactionUpdate, repo: FinanceRepository = Depends(get_repo)):
    return svc.update_transaction(repo, transaction_id, body)


@router.delete("/transactions/{transaction_id}", status_code=204, tags=["Transactions"])
@service_errors
def delete_transaction(transaction_id: int, repo: FinanceRepository = Depends(get_repo)):
    svc.delete_transaction(repo, transaction_id)
    return Response(status_code=204)


@router.post("/transactions/import", response_model=ImportResult, status_code=201, tags=["Transactions"])
@service_errors
def import_transactions(
    account_id: int = Query(gt=0),
    file: UploadFile = File(description="CSV with columns date,amount,description,category"),
    repo: FinanceRepository = Depends(get_repo),
):
    content = file.file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "CSV file is larger than 1 MB")
    return ImportResult(imported=svc.import_transactions_csv(repo, account_id, content), errors=[])


# ----------------------------------------------------------------- budgets
@router.get("/budgets", response_model=list[BudgetStatus], tags=["Budgets"])
def list_budgets(repo: FinanceRepository = Depends(get_repo)):
    return svc.budget_overview(repo)


@router.put("/budgets/{category}", response_model=BudgetStatus, tags=["Budgets"])
def set_budget(category: Category, body: BudgetUpsert, repo: FinanceRepository = Depends(get_repo)):
    svc.upsert_budget(repo, category, body.monthly_limit)
    return next(b for b in svc.budget_overview(repo) if b.category == category)


@router.delete("/budgets/{category}", status_code=204, tags=["Budgets"])
@service_errors
def delete_budget(category: Category, repo: FinanceRepository = Depends(get_repo)):
    svc.delete_budget(repo, category)
    return Response(status_code=204)


# ---------------------------------------------------------------- holdings
@router.get("/holdings", response_model=list[HoldingOut], tags=["Holdings"])
def list_holdings(repo: FinanceRepository = Depends(get_repo)):
    return [svc.holding_out(h) for h in repo.holdings()]


@router.post("/holdings", response_model=HoldingOut, status_code=201, tags=["Holdings"])
@service_errors
def create_holding(body: HoldingCreate, repo: FinanceRepository = Depends(get_repo)):
    return svc.create_holding(repo, body)


@router.patch("/holdings/{holding_id}", response_model=HoldingOut, tags=["Holdings"])
@service_errors
def update_holding(holding_id: int, body: HoldingUpdate, repo: FinanceRepository = Depends(get_repo)):
    return svc.update_holding(repo, holding_id, body)


@router.delete("/holdings/{holding_id}", status_code=204, tags=["Holdings"])
@service_errors
def delete_holding(holding_id: int, repo: FinanceRepository = Depends(get_repo)):
    svc.delete_holding(repo, holding_id)
    return Response(status_code=204)
