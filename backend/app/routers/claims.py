from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AuditLog, Campaign, Claim
from app.schemas.api import ClaimRead, ClaimReview
from app.services.auth import get_current_wallet, require_issuer
from app.services.storage import save_evidence


router = APIRouter(tags=["claims"])


@router.post("/campaigns/{campaign_id}/claims", response_model=ClaimRead, status_code=201)
def submit_claim(
    campaign_id: int,
    student_name: str = Form(min_length=2, max_length=120),
    student_email: str = Form(min_length=5, max_length=200),
    evidence: UploadFile = File(),
    wallet: str = Depends(get_current_wallet),
    db: Session = Depends(get_db),
) -> Claim:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.status != "active":
        raise HTTPException(status_code=404, detail="Active campaign not found")
    now = datetime.now(timezone.utc)
    if campaign.ends_at:
        end = campaign.ends_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < now:
            raise HTTPException(status_code=409, detail="Campaign has closed")
    if campaign.max_claims:
        total = db.scalar(
            select(func.count(Claim.id)).where(Claim.campaign_id == campaign_id)
        )
        if total and total >= campaign.max_claims:
            raise HTTPException(status_code=409, detail="Campaign claim limit reached")

    evidence_path, evidence_hash = save_evidence(evidence, wallet)
    claim = Claim(
        campaign_id=campaign_id,
        student_wallet=wallet,
        student_name=student_name.strip(),
        student_email=student_email.strip().lower(),
        evidence_path=evidence_path,
        evidence_hash=evidence_hash,
    )
    db.add(claim)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already claimed this campaign") from exc
    db.add(
        AuditLog(
            actor_wallet=wallet,
            action="claim.submitted",
            entity_type="claim",
            entity_id=str(claim.id),
            details=evidence_hash,
        )
    )
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/claims/mine", response_model=list[ClaimRead])
def list_my_claims(
    wallet: str = Depends(get_current_wallet), db: Session = Depends(get_db)
) -> list[Claim]:
    statement = (
        select(Claim)
        .where(Claim.student_wallet == wallet)
        .order_by(Claim.submitted_at.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/issuer/claims", response_model=list[ClaimRead])
def list_issuer_claims(
    issuer_wallet: str = Depends(require_issuer), db: Session = Depends(get_db)
) -> list[Claim]:
    statement = (
        select(Claim)
        .join(Campaign)
        .where(Campaign.issuer_wallet == issuer_wallet)
        .order_by(Claim.submitted_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post("/issuer/claims/{claim_id}/review", response_model=ClaimRead)
def review_claim(
    claim_id: int,
    payload: ClaimReview,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> Claim:
    claim = db.scalar(
        select(Claim)
        .join(Campaign)
        .where(Claim.id == claim_id, Campaign.issuer_wallet == issuer_wallet)
    )
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == "issued":
        raise HTTPException(status_code=409, detail="Issued claim cannot be reviewed")
    claim.status = payload.status
    claim.review_note = payload.note
    claim.reviewed_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor_wallet=issuer_wallet,
            action=f"claim.{payload.status}",
            entity_type="claim",
            entity_id=str(claim.id),
            details=payload.note,
        )
    )
    db.commit()
    db.refresh(claim)
    return claim
