"""HTTP-эндпойнты рассылок."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.modules.campaigns import service
from app.modules.campaigns.models import Campaign
from app.modules.campaigns.schemas import (
    CampaignCreate,
    CampaignRead,
    CampaignStats,
    CampaignUpdate,
)

router = APIRouter()


@router.get("", response_model=list[CampaignRead])
def list_all(db: DbSession, user: CurrentUser) -> list[CampaignRead]:
    campaigns = db.scalars(select(Campaign).order_by(Campaign.created_at.desc())).all()
    return [CampaignRead.model_validate(c) for c in campaigns]


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create(payload: CampaignCreate, db: DbSession, user: CurrentUser) -> CampaignRead:
    try:
        campaign = service.create_campaign(db, payload, created_by_id=user.id)
    except service.CampaignError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return CampaignRead.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignRead)
def get(campaign_id: int, db: DbSession, user: CurrentUser) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Рассылка не найдена")
    return CampaignRead.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update(
    campaign_id: int, payload: CampaignUpdate, db: DbSession, user: CurrentUser
) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Рассылка не найдена")

    data = payload.model_dump(exclude_unset=True)
    if "segment_filter" in data:
        data["segment_filter"] = data["segment_filter"]
    for field, value in data.items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/send", response_model=CampaignRead)
def send(campaign_id: int, db: DbSession, user: CurrentUser) -> CampaignRead:
    """Запустить рассылку (кнопка «Отправить»)."""
    try:
        campaign = service.start_campaign(db, campaign_id)
    except service.CampaignError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return CampaignRead.model_validate(campaign)


@router.post("/{campaign_id}/cancel", response_model=CampaignRead)
def cancel(campaign_id: int, db: DbSession, user: CurrentUser) -> CampaignRead:
    try:
        campaign = service.cancel_campaign(db, campaign_id)
    except service.CampaignError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return CampaignRead.model_validate(campaign)


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
def stats(campaign_id: int, db: DbSession, user: CurrentUser) -> CampaignStats:
    if db.get(Campaign, campaign_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Рассылка не найдена")
    return service.get_stats(db, campaign_id)
