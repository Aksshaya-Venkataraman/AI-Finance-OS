from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.app.models.finance import ACCOUNT_TYPES, ASSET_CLASSES, CATEGORIES

Category = Literal[CATEGORIES]  # type: ignore[valid-type]
AccountType = Literal[ACCOUNT_TYPES]  # type: ignore[valid-type]
AssetClass = Literal[ASSET_CLASSES]  # type: ignore[valid-type]

# Free text never contains angle brackets or control characters, so stored
# values cannot carry HTML/script payloads into a future web UI.
SafeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^<>\x00-\x1f\x7f]+$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, pattern=r"^[^<>\x00-\x1f\x7f]+$")]
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2, ge=Decimal("-999999999999.99"))]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- accounts
class AccountCreate(_Strict):
    name: Name
    account_type: AccountType
    currency: Currency = "GBP"
    opening_balance: Money = Decimal("0")


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
    currency: str
    opening_balance: Decimal
    balance: Decimal
    created_at: datetime


# ------------------------------------------------------------ transactions
class TransactionCreate(_Strict):
    account_id: int = Field(gt=0)
    booked_on: date
    amount: Money
    description: SafeText
    category: Category

    @field_validator("amount")
    @classmethod
    def _non_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount cannot be zero")
        return value

    @field_validator("booked_on")
    @classmethod
    def _plausible_date(cls, value: date) -> date:
        if value.year < 1990 or value > date.today().replace(year=date.today().year + 1):
            raise ValueError("booked_on is outside the supported range")
        return value


class TransactionUpdate(_Strict):
    description: SafeText | None = None
    category: Category | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    booked_on: date
    amount: Decimal
    description: str
    category: str
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


class ImportResult(BaseModel):
    imported: int
    errors: list[str]


# ----------------------------------------------------------------- budgets
class BudgetUpsert(_Strict):
    monthly_limit: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class BudgetStatus(BaseModel):
    category: str
    monthly_limit: Decimal
    spent_this_month: Decimal
    remaining: Decimal
    percent_used: float
    status: Literal["ok", "warning", "over"]


# ---------------------------------------------------------------- holdings
class HoldingCreate(_Strict):
    symbol: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9.\-]{1,15}$")]
    name: Name
    asset_class: AssetClass
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
    cost_basis: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
    current_price: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=4)]


class HoldingUpdate(_Strict):
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)] | None = None
    cost_basis: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)] | None = None
    current_price: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=4)] | None = None


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str
    asset_class: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealised_gain: Decimal
    updated_at: datetime
