from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.oauth2 import oauth2_scheme
from backend.app.core.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.models.user import User

_UNAUTHORISED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise _UNAUTHORISED from None

    user = db.get(User, user_id)
    # Checked on every request, so deactivation takes effect immediately.
    if user is None or not user.is_active:
        raise _UNAUTHORISED
    request.state.user_id = user.id
    return user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
