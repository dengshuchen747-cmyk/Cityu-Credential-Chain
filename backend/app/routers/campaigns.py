import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AuditLog, Campaign
from app.schemas.api import CampaignCreate, CampaignRead
from app.services.auth import require_issuer


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def make_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{slug or 'campaign'}-{secrets.token_hex(3)}"


@router.get("", response_model=list[CampaignRead])
def list_campaigns(
    status: str | None = Query(default="active"),
    db: Session = Depends(get_db),
) -> list[Campaign]:
    statement = select(Campaign).order_by(Campaign.created_at.desc())
    if status:
        statement = statement.where(Campaign.status == status)
    return list(db.scalars(statement).all())


@router.get("/{slug}", response_model=CampaignRead)
def get_campaign(slug: str, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.scalar(select(Campaign).where(Campaign.slug == slug))
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> Campaign:
    if payload.starts_at and payload.ends_at and payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="ends_at must be after starts_at")
    campaign = Campaign(
        slug=make_slug(payload.title),
        issuer_wallet=issuer_wallet,
        **payload.model_dump(),
    )
    db.add(campaign)
    db.flush()
    db.add(
        AuditLog(
            actor_wallet=issuer_wallet,
            action="campaign.created",
            entity_type="campaign",
            entity_id=str(campaign.id),
            details=campaign.title,
        )
    )
    db.commit()
    db.refresh(campaign)
    return campaign
