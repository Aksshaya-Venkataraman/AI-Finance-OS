from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC

from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_password_reset_token,
)
from backend.app.models.password_reset_token import PasswordResetToken

from backend.app.models.user import User

from backend.app.schemas.user import (
    UserCreate,
    Token,
    UserUpdate,
    ChangePassword,
)


def create_user(db: Session, user: UserCreate) -> User:
    # Check if email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise ValueError("Email already registered")

    # Hash the password
    hashed_password = hash_password(user.password)

    # Create a new user
    new_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_password,
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Token:

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise ValueError("Invalid email or password")

    if not verify_password(
        password,
        user.hashed_password,
    ):
        raise ValueError("Invalid email or password")

    access_token = create_access_token(
        data={
            "sub": user.email
        }
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
    )


def update_user(
    db: Session,
    current_user: User,
    user_update: UserUpdate,
) -> User:

    # Update full name if provided
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    # Update email if provided
    if (
        user_update.email is not None
        and user_update.email != current_user.email
    ):
        existing_user = (
            db.query(User)
            .filter(User.email == user_update.email)
            .first()
        )

        if existing_user:
            raise ValueError("Email already registered")

        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)

    return current_user


def change_password(
    db: Session,
    current_user: User,
    password_data: ChangePassword,
) -> None:

    # Verify current password
    if not verify_password(
        password_data.current_password,
        current_user.hashed_password,
    ):
        raise ValueError("Current password is incorrect")

    # Prevent reusing the same password
    if verify_password(
        password_data.new_password,
        current_user.hashed_password,
    ):
        raise ValueError(
            "New password must be different from the current password"
        )

    # Hash the new password
    current_user.hashed_password = hash_password(
        password_data.new_password
    )

    # Save changes
    db.commit()

def deactivate_user(
    db: Session,
    current_user: User,
) -> User:

    current_user.is_active = False

    db.commit()
    db.refresh(current_user)

    return current_user

def create_password_reset_request(
    db: Session,
    email: str,
) -> str:

    # Find the user
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise ValueError("User not found")

    # Generate secure reset token
    token = create_password_reset_token()

    # Token expires after 30 minutes
    expires_at = datetime.now(UTC) + timedelta(minutes=30)

    # Create reset-token record
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )

    # Save to database
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    return token