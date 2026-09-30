"""HTTP-эндпойнты настроек."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import DbSession, require_role
from app.modules.auth.models import UserRole
from app.modules.settings import service
from app.modules.settings.schemas import SettingItem, SettingUpdate

router = APIRouter()


@router.get(
    "",
    response_model=list[SettingItem],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_settings(db: DbSession) -> list[SettingItem]:
    return [SettingItem(**item) for item in service.list_all(db)]


@router.put(
    "/{key}",
    response_model=SettingItem,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_setting(key: str, payload: SettingUpdate, db: DbSession) -> SettingItem:
    if key not in service.KNOWN_SETTINGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Неизвестная настройка: {key}",
        )
    if payload.value is None or payload.value == "":
        service.delete_value(db, key)
    else:
        service.set_value(db, key, payload.value)

    # Вернём обновлённый item
    items = service.list_all(db)
    for it in items:
        if it["key"] == key:
            return SettingItem(**it)
    raise HTTPException(status_code=500, detail="not found after update")
