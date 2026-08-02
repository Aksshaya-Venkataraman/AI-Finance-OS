from fastapi import Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.core.oauth2 import oauth2_scheme
from backend.app.core.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.models.user import User

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return user

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )