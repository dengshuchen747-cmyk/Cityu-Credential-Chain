from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import (
    AuthResponse,
    NonceRequest,
    NonceResponse,
    VerifySignatureRequest,
)
from app.services.auth import build_nonce, verify_wallet_signature
from app.services.blockchain import blockchain
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/nonce", response_model=NonceResponse)
def request_nonce(payload: NonceRequest, db: Session = Depends(get_db)) -> NonceResponse:
    record = build_nonce(db, payload.wallet_address)
    return NonceResponse(
        wallet_address=record.wallet_address,
        message=record.message,
        expires_at=record.expires_at,
    )


@router.post("/verify", response_model=AuthResponse)
def verify_signature(
    payload: VerifySignatureRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    token = verify_wallet_signature(db, payload.wallet_address, payload.signature)
    wallet = payload.wallet_address.lower()
    is_issuer = wallet in settings.issuer_wallet_set or (
        blockchain.configured and blockchain.is_issuer(wallet)
    )
    is_admin = blockchain.configured and blockchain.is_admin(wallet)
    return AuthResponse(
        access_token=token,
        wallet_address=wallet,
        is_issuer=is_issuer,
        is_admin=is_admin,
    )
