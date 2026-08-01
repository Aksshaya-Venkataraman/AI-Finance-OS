from sqlalchemy.orm import Session

from backend.app.core.security import (hash_password, verify_password, create_access_token,)
from backend.app.models.user import User
from backend.app.schemas.user import (UserCreate, Token,)

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
