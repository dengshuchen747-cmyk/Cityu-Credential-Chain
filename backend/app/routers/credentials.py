import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from web3 import Web3

from app.core.config import settings
from app.core.database import get_db
from app.models import AuditLog, Campaign, Claim, Credential, ShareGrant
from app.schemas.api import (
    CredentialIssuePreparation,
    CredentialRead,
    CredentialRevokeConfirmation,
    CredentialRevokePreparation,
    CredentialVerification,
    PublicCredential,
    RevokeCredentialRequest,
    ShareCreate,
    ShareCreated,
    ShareView,
    StudentCredentialPortfolio,
    TransactionConfirmation,
)
from app.services.auth import get_current_wallet, normalize_wallet, require_issuer
from app.services.blockchain import blockchain
from app.services.credential_hash import build_credential_hash


router = APIRouter(tags=["credentials"])


def _claim_for_issuer(claim_id: int, issuer_wallet: str, db: Session) -> Claim:
    claim = db.scalar(
        select(Claim)
        .options(joinedload(Claim.campaign), joinedload(Claim.credential))
        .where(Claim.id == claim_id)
    )
    if claim is None or claim.campaign.issuer_wallet != issuer_wallet:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def _credential_for_issuer(
    token_id: int, issuer_wallet: str, db: Session
) -> Credential:
    credential = db.scalar(
        select(Credential).where(
            Credential.token_id == token_id,
            Credential.issuer_wallet == issuer_wallet,
        )
    )
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential


@router.post(
    "/issuer/claims/{claim_id}/issue/prepare",
    response_model=CredentialIssuePreparation,
)
def prepare_claim_issuance(
    claim_id: int,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> CredentialIssuePreparation:
    claim = _claim_for_issuer(claim_id, issuer_wallet, db)
    if claim.status != "approved":
        raise HTTPException(
            status_code=409, detail="Claim must be approved before issuance"
        )
    if claim.credential is not None:
        raise HTTPException(status_code=409, detail="Credential already issued")

    data_hash = build_credential_hash(claim.campaign, claim)
    existing_token_id = blockchain.token_id_by_data_hash(data_hash)
    if existing_token_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Credential already exists on-chain as token #{existing_token_id}; "
                "run credential reconciliation"
            ),
        )
    metadata_uri = claim.campaign.metadata_uri or f"ipfs://pending/{data_hash[2:]}"
    transaction = blockchain.prepare_issue_credential(
        claim.student_wallet, data_hash, metadata_uri
    )
    return CredentialIssuePreparation(
        claim_id=claim.id,
        student_wallet=claim.student_wallet,
        data_hash=data_hash,
        metadata_uri=metadata_uri,
        transaction=transaction,
    )


@router.post(
    "/issuer/claims/{claim_id}/issue/confirm", response_model=CredentialRead
)
def confirm_claim_issuance(
    claim_id: int,
    payload: TransactionConfirmation,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> Credential:
    claim = _claim_for_issuer(claim_id, issuer_wallet, db)
    if claim.status != "approved":
        raise HTTPException(
            status_code=409, detail="Claim must be approved before issuance"
        )
    if claim.credential is not None:
        raise HTTPException(status_code=409, detail="Credential already issued")

    data_hash = build_credential_hash(claim.campaign, claim)
    metadata_uri = claim.campaign.metadata_uri or f"ipfs://pending/{data_hash[2:]}"
    chain_result = blockchain.confirm_issue_credential(
        payload.transaction_hash,
        issuer_wallet,
        claim.student_wallet,
        data_hash,
        metadata_uri,
    )
    credential = Credential(
        claim_id=claim.id,
        token_id=chain_result["token_id"],
        contract_address=settings.credential_contract_address.lower(),
        transaction_hash=chain_result["transaction_hash"],
        data_hash=data_hash,
        metadata_uri=metadata_uri,
        issuer_wallet=chain_result["issuer_wallet"],
    )
    claim.status = "issued"
    db.add(credential)
    db.flush()
    db.add(
        AuditLog(
            actor_wallet=issuer_wallet,
            action="credential.issued",
            entity_type="credential",
            entity_id=str(credential.id),
            details=credential.transaction_hash,
        )
    )
    db.commit()
    db.refresh(credential)
    return credential


@router.get("/credentials/mine", response_model=list[CredentialRead])
def list_my_credentials(
    wallet: str = Depends(get_current_wallet), db: Session = Depends(get_db)
) -> list[Credential]:
    statement = (
        select(Credential)
        .join(Claim)
        .where(Claim.student_wallet == wallet)
        .order_by(Credential.issued_at.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/issuer/credentials", response_model=list[CredentialRead])
def list_issuer_credentials(
    issuer_wallet: str = Depends(require_issuer), db: Session = Depends(get_db)
) -> list[Credential]:
    statement = (
        select(Credential)
        .where(Credential.issuer_wallet == issuer_wallet)
        .order_by(Credential.issued_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "/issuer/credentials/{token_id}/revoke/prepare",
    response_model=CredentialRevokePreparation,
)
def prepare_credential_revocation(
    token_id: int,
    payload: RevokeCredentialRequest,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> CredentialRevokePreparation:
    credential = _credential_for_issuer(token_id, issuer_wallet, db)
    if credential.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Credential is already revoked")
    reason_hash = Web3.keccak(text=payload.reason).hex()
    transaction = blockchain.prepare_revoke_credential(token_id, reason_hash)
    return CredentialRevokePreparation(
        token_id=token_id,
        reason=payload.reason,
        reason_hash=reason_hash,
        transaction=transaction,
    )


@router.post(
    "/issuer/credentials/{token_id}/revoke/confirm",
    response_model=CredentialRead,
)
def confirm_credential_revocation(
    token_id: int,
    payload: CredentialRevokeConfirmation,
    issuer_wallet: str = Depends(require_issuer),
    db: Session = Depends(get_db),
) -> Credential:
    credential = _credential_for_issuer(token_id, issuer_wallet, db)
    if credential.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Credential is already revoked")
    reason_hash = Web3.keccak(text=payload.reason).hex()
    transaction_hash = blockchain.confirm_revoke_credential(
        payload.transaction_hash,
        issuer_wallet,
        token_id,
        reason_hash,
    )
    credential.revoked_at = datetime.now(timezone.utc)
    credential.revocation_reason = payload.reason
    db.add(
        AuditLog(
            actor_wallet=issuer_wallet,
            action="credential.revoked",
            entity_type="credential",
            entity_id=str(credential.id),
            details=transaction_hash,
        )
    )
    db.commit()
    db.refresh(credential)
    return credential


@router.get(
    "/public/students/{wallet}/credentials",
    response_model=StudentCredentialPortfolio,
)
def list_public_student_credentials(
    wallet: str, db: Session = Depends(get_db)
) -> StudentCredentialPortfolio:
    normalized_wallet = normalize_wallet(wallet)
    statement = (
        select(Credential)
        .join(Claim)
        .options(joinedload(Credential.claim).joinedload(Claim.campaign))
        .where(Claim.student_wallet == normalized_wallet)
        .order_by(Credential.issued_at.desc())
    )
    credentials = list(db.scalars(statement).all())
    public_credentials: list[PublicCredential] = []
    for credential in credentials:
        chain_available = False
        valid = credential.revoked_at is None
        revoked = credential.revoked_at is not None
        student_wallet = credential.claim.student_wallet
        issuer_wallet = credential.issuer_wallet
        issued_at = credential.issued_at
        metadata_uri = credential.metadata_uri
        if blockchain.configured:
            try:
                result = blockchain.verify_credential(
                    credential.token_id, credential.data_hash
                )
                chain_available = True
                student_wallet = result["student_wallet"]
                issuer_wallet = result["issuer_wallet"]
                issued_at = result["issued_at"] or issued_at
                metadata_uri = result["metadata_uri"]
                revoked = result["revoked"]
                valid = result["valid"] and student_wallet == normalized_wallet
            except HTTPException:
                chain_available = False

        campaign = credential.claim.campaign
        public_credentials.append(
            PublicCredential(
                token_id=credential.token_id,
                campaign_title=campaign.title,
                campaign_description=campaign.description,
                credential_type=campaign.credential_type,
                student_wallet=student_wallet,
                issuer_wallet=issuer_wallet,
                issued_at=issued_at,
                valid=valid,
                revoked=revoked,
                chain_available=chain_available,
                metadata_uri=metadata_uri,
                transaction_hash=credential.transaction_hash,
                contract_address=credential.contract_address,
                network=credential.network,
            )
        )
    return StudentCredentialPortfolio(
        student_wallet=normalized_wallet,
        credentials=public_credentials,
    )


@router.get("/credentials/{token_id}", response_model=CredentialVerification)
def verify_credential(
    token_id: int,
    submitted_hash: str | None = Query(default=None, min_length=66, max_length=66),
    db: Session = Depends(get_db),
) -> CredentialVerification:
    credential = db.scalar(
        select(Credential)
        .options(joinedload(Credential.claim))
        .where(Credential.token_id == token_id)
    )
    if credential is None and submitted_hash is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Credential is not indexed locally; provide submitted_hash "
                "for chain verification"
            ),
        )
    data_hash = submitted_hash or credential.data_hash
    if blockchain.configured:
        result = blockchain.verify_credential(token_id, data_hash)
        return CredentialVerification(
            token_id=token_id,
            chain_available=True,
            transaction_hash=credential.transaction_hash if credential else "",
            **result,
        )

    if credential is None:
        raise HTTPException(
            status_code=503, detail="Blockchain connection is not configured"
        )
    return CredentialVerification(
        token_id=token_id,
        chain_available=False,
        valid=(
            credential.revoked_at is None
            and data_hash.lower() == credential.data_hash.lower()
        ),
        hash_matches=data_hash.lower() == credential.data_hash.lower(),
        revoked=credential.revoked_at is not None,
        student_wallet=credential.claim.student_wallet,
        issuer_wallet=credential.issuer_wallet,
        issued_at=credential.issued_at,
        metadata_uri=credential.metadata_uri,
        transaction_hash=credential.transaction_hash,
    )


@router.post(
    "/credentials/{token_id}/shares",
    response_model=ShareCreated,
    status_code=201,
    deprecated=True,
)
def create_share(
    token_id: int,
    payload: ShareCreate,
    wallet: str = Depends(get_current_wallet),
    db: Session = Depends(get_db),
) -> ShareCreated:
    credential = db.scalar(
        select(Credential)
        .options(joinedload(Credential.claim))
        .where(Credential.token_id == token_id)
    )
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    if credential.claim.student_wallet != wallet:
        raise HTTPException(
            status_code=403, detail="Only the credential holder can share it"
        )
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=payload.expires_in_hours
    )
    grant = ShareGrant(
        credential_id=credential.id,
        token_hash=token_hash,
        verifier_wallet=(
            payload.verifier_wallet.lower() if payload.verifier_wallet else None
        ),
        expires_at=expires_at,
    )
    db.add(grant)
    db.commit()
    return ShareCreated(share_token=raw_token, expires_at=expires_at)


@router.get("/shares/{share_token}", response_model=ShareView, deprecated=True)
def view_share(share_token: str, db: Session = Depends(get_db)) -> ShareView:
    token_hash = hashlib.sha256(share_token.encode()).hexdigest()
    grant = db.scalar(
        select(ShareGrant)
        .options(
            joinedload(ShareGrant.credential)
            .joinedload(Credential.claim)
            .joinedload(Claim.campaign)
        )
        .where(ShareGrant.token_hash == token_hash)
    )
    now = datetime.now(timezone.utc)
    if grant is None or grant.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Share link not found")
    expires_at = grant.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=410, detail="Share link has expired")
    credential = grant.credential
    return ShareView(
        token_id=credential.token_id,
        credential_type=credential.claim.campaign.credential_type,
        student_name=credential.claim.student_name,
        student_email=credential.claim.student_email,
        issuer_wallet=credential.issuer_wallet,
        issued_at=credential.issued_at,
        revoked=credential.revoked_at is not None,
    )
