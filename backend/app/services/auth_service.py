from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate

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