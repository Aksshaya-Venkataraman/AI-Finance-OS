from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints


def _password_policy(value: str) -> str:
    # Length beats complexity rules (NIST SP 800-63B); reject trivial repeats.
    if len(set(value)) < 6:
        raise ValueError("Password is too repetitive")
    return value


Password = Annotated[str, StringConstraints(min_length=12, max_length=128), AfterValidator(_password_policy)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^<>\x00-\x1f\x7f]+$")]
Email = Annotated[EmailStr, AfterValidator(str.lower)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserBase(_Strict):
    full_name: FullName
    email: Email


class UserCreate(UserBase):
    password: Password


class UserLogin(_Strict):
    email: Email
    password: Annotated[str, StringConstraints(max_length=128)]


class ForgotPasswordRequest(_Strict):
    email: Email


class ResetPasswordRequest(_Strict):
    token: Annotated[str, StringConstraints(min_length=20, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]
    new_password: Password


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth token type, not a secret


class UserUpdate(_Strict):
    full_name: FullName | None = None
    email: Email | None = None


class ChangePassword(_Strict):
    current_password: Annotated[str, StringConstraints(max_length=128)]
    new_password: Password


class MessageResponse(BaseModel):
    message: str
