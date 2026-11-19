from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_superuser, get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import ChangePassword, MessageResponse, UserResponse, UserUpdate
from backend.app.services.auth_service import change_password, deactivate_user, update_user

router = APIRouter(prefix="/users", tags=["Users"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_superuser)])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_user(db=db, current_user=current_user, user_update=user_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/change-password", response_model=MessageResponse)
def change_my_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_password(db=db, current_user=current_user, password_data=password_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return MessageResponse(message="Password changed successfully")


@router.post("/deactivate", response_model=MessageResponse)
def deactivate_my_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deactivate_user(db=db, current_user=current_user)
    return MessageResponse(message="Account deactivated successfully")


@admin_router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
