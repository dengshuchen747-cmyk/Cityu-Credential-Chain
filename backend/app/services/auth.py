import secrets
from datetime import datetime, timedelta, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import Depends, Header, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session
from web3 import Web3

from app.core.config import settings
from app.core.database import get_db
from app.models import WalletNonce


serializer = URLSafeTimedSerializer(settings.secret_key, salt="wallet-session")


def normalize_wallet(wallet: str) -> str:
    if not Web3.is_address(wallet):
        raise HTTPException(status_code=422, detail="Invalid Ethereum wallet address")
    return Web3.to_checksum_address(wallet).lower()


def build_nonce(db: Session, wallet: str) -> WalletNonce:
    normalized = normalize_wallet(wallet)
    now = datetime.now(timezone.utc)
    nonce = secrets.token_urlsafe(24)
    expires_at = now + timedelta(minutes=settings.nonce_ttl_minutes)
    message = (
        "CityU Credential Chain login\n"
        f"Wallet: {normalized}\n"
        f"Nonce: {nonce}\n"
        f"Expires: {expires_at.isoformat()}"
    )
    record = db.get(WalletNonce, normalized)
    if record is None:
        record = WalletNonce(
            wallet_address=normalized,
            nonce=nonce,
            message=message,
            expires_at=expires_at,
        )
        db.add(record)
    else:
        record.nonce = nonce
        record.message = message
        record.expires_at = expires_at
        record.used_at = None
    db.commit()
    db.refresh(record)
    return record


def verify_wallet_signature(db: Session, wallet: str, signature: str) -> str:
    normalized = normalize_wallet(wallet)
    record = db.get(WalletNonce, normalized)
    now = datetime.now(timezone.utc)
    if record is None or record.used_at is not None:
        raise HTTPException(status_code=400, detail="Request a fresh login nonce")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=400, detail="Login nonce has expired")

    try:
        recovered = Account.recover_message(
            encode_defunct(text=record.message), signature=signature
        ).lower()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid wallet signature") from exc
    if recovered != normalized:
        raise HTTPException(status_code=401, detail="Signature does not match wallet")

    record.used_at = now
    db.commit()
    return serializer.dumps({"wallet": normalized})


def parse_session_token(token: str) -> str:
    try:
        payload = serializer.loads(
            token, max_age=settings.auth_token_max_age_seconds
        )
    except SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="Login session expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="Invalid login session") from exc
    return str(payload["wallet"])


def get_current_wallet(
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet login required",
        )
    return parse_session_token(authorization.split(" ", 1)[1])


def require_issuer(wallet: str = Depends(get_current_wallet)) -> str:
    from app.services.blockchain import blockchain

    if wallet in settings.issuer_wallet_set:
        return wallet
    if blockchain.configured and blockchain.is_issuer(wallet):
        return wallet
    raise HTTPException(status_code=403, detail="Issuer role required")


def require_admin(wallet: str = Depends(get_current_wallet)) -> str:
    from app.services.blockchain import blockchain

    if blockchain.configured and blockchain.is_admin(wallet):
        return wallet
    raise HTTPException(status_code=403, detail="Contract administrator role required")
