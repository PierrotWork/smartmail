"""Бизнес-логика авторизации: регистрация, логин, обновление токенов."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import TokenPair, UserCreate


class AuthError(Exception):
    pass


def create_user(db: Session, data: UserCreate) -> User:
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise AuthError("Пользователь с таким email уже существует")

    user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Неверный email или пароль")
    if not user.is_active:
        raise AuthError("Учётная запись отключена")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, extra={"role": user.role.value}),
        refresh_token=create_refresh_token(user.id),
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except ValueError as e:
        raise AuthError("Некорректный refresh-токен") from e

    if payload.get("type") != "refresh":
        raise AuthError("Токен не является refresh-токеном")

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("Пользователь недоступен")

    return issue_tokens(user)


def ensure_bootstrap_admin(db: Session, email: str, password: str, name: str = "Admin") -> None:
    """Создать первого администратора, если пользователей нет."""
    has_any = db.scalar(select(User).limit(1)) is not None
    if has_any:
        return
    admin = User(
        email=email,
        name=name,
        role=UserRole.ADMIN,
        password_hash=hash_password(password),
    )
    db.add(admin)
    db.commit()
