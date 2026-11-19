from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.rate_limit import limit_by_ip
from backend.app.database.session import get_db
from backend.app.schemas.user import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
)
from backend.app.services.auth_service import (
    authenticate_user,
    create_password_reset_request,
    create_user,
    reset_password,
)
from backend.app.services.email_service import send_password_reset

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_REQUESTED = "If an account exists for that email, a reset link has been sent."


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_ip("register", "REGISTER_RATE_LIMIT"))],
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/login", response_model=Token, dependencies=[Depends(limit_by_ip("login", "LOGIN_RATE_LIMIT"))])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if len(form_data.username) > 255 or len(form_data.password) > 128:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    try:
        return authenticate_user(db=db, email=form_data.username, password=form_data.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("password-reset", "PASSWORD_RESET_RATE_LIMIT"))],
)
def forgot_password(request: ForgotPasswordRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    # The token is only ever emailed, never returned, and the response is the
    # same whether or not the address is registered.
    created = create_password_reset_request(db=db, email=request.email)
    if created is not None:
        user, token = created
        background.add_task(send_password_reset, user.email, token)
    return MessageResponse(message=RESET_REQUESTED)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(limit_by_ip("password-reset", "PASSWORD_RESET_RATE_LIMIT"))],
)
def reset_password_endpoint(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        reset_password(db, request.token, request.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return MessageResponse(message="Password has been reset. You can now log in.")
