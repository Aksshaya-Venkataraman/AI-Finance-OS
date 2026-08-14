from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (UserResponse, UserUpdate, ChangePassword,)
from backend.app.services.auth_service import (update_user, change_password, deactivate_user,)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.put(
    "/me",
    response_model=UserResponse,
)
def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_user(
            db=db,
            current_user=current_user,
            user_update=user_update,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/change-password")
def change_my_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_password(
            db=db,
            current_user=current_user,
            password_data=password_data,
        )

        return {
            "message": "Password changed successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

@router.post("/deactivate")
def deactivate_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        deactivate_user(
            db=db,
            current_user=current_user,
        )

        return {
            "message": "Account deactivated successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )