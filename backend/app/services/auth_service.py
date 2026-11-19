from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    hash_reset_token,
    password_needs_rehash,
    verify_password,
)
from backend.app.database.base import utcnow
from backend.app.models.password_reset_token import PasswordResetToken
from backend.app.models.user import User
from backend.app.schemas.user import ChangePassword, Token, UserCreate, UserUpdate

# Deliberately vague messages: they must not reveal which emails are registered.
REGISTRATION_FAILED = "Registration failed"
INVALID_LOGIN = "Invalid email or password"
INVALID_RESET = "Invalid or expired reset token"


def _find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, user: UserCreate) -> User:
    if _find_by_email(db, user.email) is not None:
        raise ValueError(REGISTRATION_FAILED)
    new_user = User(
        full_name=user.full_name,
        email=user.email.lower(),
        hashed_password=hash_password(user.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:  # concurrent registration with the same email
        db.rollback()
        raise ValueError(REGISTRATION_FAILED) from None
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> Token:
    user = _find_by_email(db, email)
    # verify_password(None) still spends the full hashing time.
    valid = verify_password(password, user.hashed_password if user else None)
    if user is None or not valid or not user.is_active:
        raise ValueError(INVALID_LOGIN)
    if password_needs_rehash(user.hashed_password):
        # Upgrades bcrypt hashes from the previous version to Argon2id on login.
        user.hashed_password = hash_password(password)
        db.commit()
    return Token(access_token=create_access_token(user.id))


def update_user(db: Session, current_user: User, user_update: UserUpdate) -> User:
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.email is not None and user_update.email != current_user.email:
        if _find_by_email(db, user_update.email) is not None:
            raise ValueError("This email address cannot be used")
        current_user.email = user_update.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("This email address cannot be used") from None
    db.refresh(current_user)
    return current_user


def change_password(db: Session, current_user: User, password_data: ChangePassword) -> None:
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise ValueError("Current password is incorrect")
    if password_data.new_password == password_data.current_password:
        raise ValueError("New password must be different from the current password")
    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()


def deactivate_user(db: Session, current_user: User) -> User:
    current_user.is_active = False
    db.commit()
    db.refresh(current_user)
    return current_user


def create_password_reset_request(db: Session, email: str) -> tuple[User, str] | None:
    """Create a single-use reset token. Returns (user, token) or None.

    The caller must send the token by email and must give the same response
    whether or not the address exists.
    """
    user = _find_by_email(db, email)
    if user is None or not user.is_active:
        return None
    _invalidate_tokens(db, user.id)
    token, token_hash = create_password_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
            used=False,
        )
    )
    db.commit()
    return user, token


def reset_password(db: Session, token: str, new_password: str) -> None:
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_reset_token(token)))
    if record is None or record.used or record.expires_at <= utcnow():
        raise ValueError(INVALID_RESET)
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise ValueError(INVALID_RESET)
    user.hashed_password = hash_password(new_password)
    _invalidate_tokens(db, user.id)
    db.commit()


def _invalidate_tokens(db: Session, user_id: int) -> None:
    db.execute(
        update(PasswordResetToken).where(PasswordResetToken.user_id == user_id, PasswordResetToken.used.is_(False)).values(used=True)
    )
