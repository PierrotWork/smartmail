"""HTTP-эндпойнты авторизации."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import CurrentUser, DbSession, require_role
from app.modules.auth import service
from app.modules.auth.models import UserRole
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)

router = APIRouter()


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    try:
        user = service.authenticate(db, payload.email, payload.password)
    except service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        return service.refresh_tokens(db, payload.refresh_token)
    except service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_user(payload: UserCreate, db: DbSession) -> UserRead:
    try:
        user = service.create_user(db, payload)
    except service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return UserRead.model_validate(user)
